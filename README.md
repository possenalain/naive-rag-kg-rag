# Naive RAG vs Knowledge Graph RAG Benchmarking

A benchmarking system to compare three RAG approaches for multi-hop question answering:
- **Naive RAG**: Vector-based retrieval (PostgreSQL + pgvector)
- **KG-RAG**: Knowledge Graph retrieval (Neo4j + Graphiti)
- **Hybrid RAG**: Combined approach

## Quick Start

### Prerequisites
- Python 3.11+
- [UV](https://github.com/astral-sh/uv) (recommended) or pip
- Docker & Docker Compose
- 8GB+ RAM

### 1. Installation

**With UV (recommended - 10x faster)**:
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
uv venv
source .venv/bin/activate
uv sync --all-extras
```

**Traditional pip**:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env - Required: Database credentials, LLM API keys
```

Example `.env`:
```bash
# Database
POSTGRES_URL=postgresql://raguser:password@localhost:5432/rag_benchmark
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your_neo4j_password

# LLM (Gemini)
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-pro
LLM_API_KEY=your_gemini_api_key

# Embedding
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL_NAME=text-embedding-004
```

### 3. Start Services & Setup

```bash
# Start PostgreSQL and Neo4j
docker-compose up -d

# Verify services are ready
docker-compose ps

# Initialize databases
uv run python -m src.utils.db init
uv run python -m src.utils.graph init

# Verify setup
uv run python setup.py
```

### 4. Run Benchmarks

```bash
# Ingest documents
uv run python cli.py ingest ./data/big_tech_docs

# Run evaluation
uv run python cli.py evaluate --num-questions 50 --dataset big_tech_curated

# Analyze results
uv run python cli.py analyze benchmarks\runs\big_tech_curated_results_J12V1/eval_*.json \
    --output-dir benchmarks\runs\big_tech_curated_results_J12V1
```


# For help
uv run python cli.py --help
```

## Project Structure

```
naive-rag-kg-rag/
├── config/                      # Configuration & settings
├── src/
│   ├── ingestion/              # Document processing
│   ├── rag_variants/           # Three RAG implementations
│   ├── evaluation/             # Benchmarking & scoring
│   ├── analysis/               # Statistical analysis & viz
│   └── utils/                  # Shared utilities
├── benchmarks/
│   ├── datasets/               # Question datasets
│   └── runs/                   # Evaluation results
├── data/                       # Documents for ingestion
├── docs/                       # Documentation
├── tests/                      # Test suite
├── cli.py                      # Command-line interface
├── setup.py                    # Setup & verification
└── docker-compose.yml          # Infrastructure
```

## Core Workflows

### Ingest Documents
```bash
# Reset and ingest
uv run python cli.py reset
uv run python cli.py ingest ./data/big_tech_docs
```

### Run Evaluation
```bash
# Run all questions
uv run python cli.py evaluate --num-questions -1 --dataset big_tech_curated \
    --output-dir ./benchmarks/runs/my_run
```

### Analyze Results
```bash
uv run python cli.py analyze ./benchmarks/runs/my_run/eval_*.json \
    --output-dir ./benchmarks/runs/my_run
```

## Evaluation Dimensions

Each answer scored 1-10 by LLM across:
- **Correctness**: Factual accuracy
- **Completeness**: Full coverage
- **Relevance**: Question alignment
- **Faithfulness**: No hallucinations
- **Clarity**: Clear expression

## Architecture

```
Evaluation Orchestrator
    ↓       ↓       ↓
Naive  KG-RAG  Hybrid
  ↓       ↓       ↓
PostgreSQL Neo4j  Both
+pgvector +Graphiti
```

**Naive RAG**: Query → Embedding → Vector Search → LLM  
**KG-RAG**: Query → Entity Extraction → Graph Traversal → LLM  
**Hybrid**: Query → Parallel Retrieval → Fusion → LLM

## Helper Scripts

```bash
make setup      # Complete setup
make test       # Run tests
make format     # Format code
make docker-up  # Start services
```

## LLM Provider Options

**Gemini** (default):
```bash
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-pro
LLM_API_KEY=your_key
```

**Ollama** (local):
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL_NAME=llama3.1
```

## Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) - Project overview
- [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) - Docker usage

## Testing

```bash
pytest                           # All tests
pytest --cov=src                # With coverage
pytest tests/test_rag_variants/ # Specific module
```

## Troubleshooting

**Service connection issues**:
```bash
docker-compose ps        # Check status
docker-compose restart   # Restart services
docker-compose logs -f   # View logs
```

**Database issues**:
```bash
uv run python setup.py   # Re-run setup
```

## License

MIT License

## Acknowledgments

- Built with Pydantic AI and Graphiti
- Inspired by Cole Medin's Agentic RAG work
