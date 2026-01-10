# Naive RAG vs Knowledge Graph RAG Benchmarking

A comprehensive benchmarking system to compare and evaluate three Retrieval-Augmented Generation (RAG) approaches for multi-hop question answering.

> 🚀 **Now using [UV](https://github.com/astral-sh/uv)** - A blazingly fast Python package manager (10-100x faster than pip)!
>
> 📚 **Setup Guides**:
> - [QUICKSTART.md](docs/QUICKSTART.md) - Quick start in 10 minutes ⚡
> - [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) - Complete setup instructions
> - [UV_MIGRATION.md](docs/UV_MIGRATION.md) - UV usage and benefits
> - [DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) - Docker usage guide

## 🎯 Project Goals

Quantitatively compare three RAG architectures:
1. **Naive RAG**: Traditional vector-based retrieval (PostgreSQL + pgvector)
2. **KG-RAG**: Knowledge Graph-based retrieval (Neo4j + Graphiti)
3. **Hybrid RAG**: Combined approach leveraging both methods

Evaluate performance on multi-hop reasoning tasks using standard benchmarks (HotpotQA, WikiMultiHopQA, MultiHop-RAG) across five dimensions:
- ✅ **Correctness**: Factual accuracy
- 📋 **Completeness**: Full coverage of answer aspects  
- 🎯 **Relevance**: Question alignment
- 🔒 **Faithfulness**: No hallucinated facts
- 💡 **Clarity**: Clear expression

## 📁 Project Structure

```
naive-rag-kg-rag/
├── docs/                            # 📚 All documentation
│   ├── README.md                    # Documentation index
│   ├── QUICKSTART.md                # Quick start guide
│   ├── SETUP_GUIDE.md               # Complete setup instructions
│   ├── UV_MIGRATION.md              # UV usage guide
│   ├── DOCKER_GUIDE.md              # Docker guide
│   ├── ARCHITECTURE.md              # System architecture
│   ├── IMPLEMENTATION_PLAN.md       # Implementation roadmap
│   └── TASKS.md                     # Task tracking
├── config/                          # Configuration management
│   ├── __init__.py
│   ├── settings.py                  # Pydantic settings
│   └── logging.yaml                 # Logging configuration
├── src/
│   ├── __init__.py
│   ├── ingestion/                   # Document processing & ingestion
│   │   ├── __init__.py
│   │   ├── loader.py               # Document loading
│   │   ├── chunker.py              # Semantic chunking
│   │   ├── embedder.py             # Embedding generation
│   │   ├── graph_builder.py        # Knowledge graph construction
│   │   └── pipeline.py             # End-to-end ingestion
│   ├── rag_variants/                # Three RAG implementations
│   │   ├── __init__.py
│   │   ├── naive_rag.py            # Vector-based RAG
│   │   ├── kg_rag.py               # Knowledge graph RAG
│   │   ├── hybrid_rag.py           # Combined approach
│   │   └── base.py                 # Base RAG interface
│   ├── evaluation/                  # Benchmarking & scoring
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Evaluation orchestrator agent
│   │   ├── scorer.py               # LLM-based scoring
│   │   ├── benchmark_loader.py     # Dataset loading
│   │   └── models.py               # Evaluation data models
│   ├── analysis/                    # Statistical analysis & visualization
│   │   ├── __init__.py
│   │   ├── statistics.py           # Statistical analysis
│   │   ├── visualizations.py       # Plot generation
│   │   └── reports.py              # Report generation
│   └── utils/                       # Shared utilities
│       ├── __init__.py
│       ├── db.py                   # Database utilities
│       ├── graph.py                # Graph database utilities
│       ├── llm.py                  # LLM provider abstraction
│       └── metrics.py              # Metrics collection
├── benchmarks/
│   ├── datasets/                    # Benchmark question datasets
│   │   └── hotpotqa_sample.json
│   └── results/                     # Evaluation outputs
│       ├── answers.json
│       ├── scores.json
│       └── figures/
├── docker/
│   ├── docker-compose.yml          # All services
│   ├── postgres/
│   │   └── Dockerfile
│   ├── neo4j/
│   │   └── Dockerfile
│   └── app/
│       └── Dockerfile
├── sql/
│   └── schema.sql                   # PostgreSQL schema
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_ingestion/
│   ├── test_rag_variants/
│   └── test_evaluation/
├── notebooks/                       # Jupyter notebooks for analysis
│   ├── 01_exploratory_analysis.ipynb
│   ├── 02_visualizations.ipynb
│   └── 03_insights.ipynb
├── data/                           # Sample documents
│   └── documents/
├── .env.example                    # Environment variables template
├── .gitignore
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Pytest configuration
├── README.md                       # This file
├── PROJECT_OVERVIEW.md             # Detailed project overview
├── IMPLEMENTATION_PLAN.md          # Implementation roadmap
├── ARCHITECTURE.md                 # Technical architecture
└── TASKS.md                        # Task tracking
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [UV](https://github.com/astral-sh/uv) (fast Python package installer) - **Recommended**
- Docker & Docker Compose
- 8GB+ RAM
- (Optional) NVIDIA GPU for local LLMs

### 1. Clone and Setup

**With UV (Recommended - 10x faster)**:
```bash
# Install UV if not already installed
# Windows PowerShell:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to project directory
cd naive-rag-kg-rag

# Create virtual environment and install dependencies
uv venv
uv sync --all-extras

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate
```

**Traditional pip method** (if UV not available):
```bash
# Navigate to project directory
cd naive-rag-kg-rag

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> 💡 **Tip**: See [UV_MIGRATION.md](docs/UV_MIGRATION.md) for detailed UV usage and migration guide.

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configurations
# Required: Database credentials, LLM API keys
```

### 3. Start Infrastructure

```bash
# Start PostgreSQL and Neo4j
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Initialize databases
uv run python -m src.utils.db init
uv run python -m src.utils.graph init
```

### 4. Ingest Documents

```bash
# With UV (recommended):
uv run python -m src.ingestion.pipeline \
    --input-dir ./data/documents \
    --embedding-provider gemini \
    --build-graph

# Check ingestion status
uv run python -m src.ingestion.pipeline --status

# Or with activated venv:
python -m src.ingestion.pipeline \
    --input-dir ./data/documents \
    --embedding-provider gemini \
  With UV (recommended):
# Run benchmark evaluation
uv run python -m src.evaluation.orchestrator \
    --dataset hotpotqa \
    --num-questions 50 \
    --output ./benchmarks/results

# Score results with LLM
uv run python -m src.evaluation.scorer \
    --answers ./benchmarks/results/answers.json \
    --output ./benchmarks/results/scores.json

# Or with activated venv:
python -m src.evaluation.orchestrator --dataset hotpotqa --num-questions 50
    --output ./benchmarks/results

# Score results with LLM
python -m src.evaluation.scorer \
    --answers ./benchmarks/results/answers.json \
    --output ./benchmarks/results/scores.json
```
With UV (recommended):
# Generate statistical analysis
uv run python -m src.analysis.statistics \
    --scores ./benchmarks/results/scores.json \
    --output ./benchmarks/results/analysis_report.md

# Generate visualizations
uv run python -m src.analysis.visualizations \
    --scores ./benchmarks/results/scores.json \
    --output-dir ./benchmarks/results/figures

# Or with activated venv:
python -m src.analysis.statistics --scores ./benchmarks/results/scores.json
```

Or use Jupyter notebooks:
```bash
# With UV:
uv run jupyter lab notebooks/

# Or with activated venv:utput-dir ./benchmarks/results/figures
```

Or use Jupyter notebooks:
```bash
jupyter lab notebooks/
```

## � Docker Usage

This project provides two Dockerfiles for different use cases:

- **`Dockerfile`** - Optimized production image (~500MB)
- **`Dockerfile.dev`** - Full development environment (~800MB)

**Quick Start**:
```bash
# Build production image
docker build -t naive-rag:latest .

# Build development image
docker build -f Dockerfile.dev -t naive-rag:dev .

# Run with docker-compose (databases only)
docker-compose up -d
```

**Recommended Workflow**: Use UV locally for development (fastest), Docker for deployment.

See [DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) for complete Docker documentation.

## �🔧 Configuration

### Helper Scripts

For convenience, use the provided helper scripts:

**Windows (PowerShell)**:
```powershell
# Show all available commands
.\make.ps1 help

# Complete setup
.\make.ps1 setup

# Run tests
.\make.ps1 test

# Format code
.\make.ps1 format

# Start Docker services
.\make.ps1 docker-up
```

**Linux/macOS (Makefile)**:
```bash
# Show all available commands
make help

# Complete setup
make setup

# Run tests
make test

# Format code
make format

# Start Docker services
make docker-up
```

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Database Configuration
POSTGRES_URL=postgresql://raguser:password@localhost:5432/rag_benchmark
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# LLM Configuration (Gemini)
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-pro
LLM_API_KEY=your_gemini_api_key
LLM_TEMPERATURE=0.7

# Or use Ollama (local)
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://localhost:11434
# LLM_MODEL_NAME=llama3.1

# Embedding Configuration
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL_NAME=text-embedding-004
EMBEDDING_DIMENSIONS=768

# Ingestion Settings
INGESTION_CHUNK_SIZE=512
INGESTION_CHUNK_OVERLAP=50
INGESTION_USE_SEMANTIC_CHUNKING=true

# Benchmark Settings
BENCHMARK_DATASET_NAME=hotpotqa
BENCHMARK_NUM_QUESTIONS=50
BENCHMARK_BATCH_SIZE=10
BENCHMARK_OUTPUT_DIR=./benchmarks/results
```

### LLM Provider Switching

The system supports multiple LLM providers:

**Google Gemini (Default)**:
```bash
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-pro  # or gemini-1.5-flash for cost savings
LLM_API_KEY=your_api_key
```

**Ollama (Local)**:
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL_NAME=llama3.1  # or mistral, qwen2.5, etc.
```

**OpenAI**:
```bash
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_key
LLM_MODEL_NAME=gpt-4-turbo
```

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────┐
│         Evaluation Orchestrator                  │
│  - Question routing                              │
│  - Parallel RAG execution                        │
│  - Response collection                           │
└─────────────────────────────────────────────────┘
            ↓           ↓           ↓
┌──────────────┬──────────────┬──────────────────┐
│  Naive RAG   │   KG-RAG     │   Hybrid RAG     │
│  (Vector DB) │   (Graph DB) │   (Combined)     │
└──────────────┴──────────────┴──────────────────┘
            ↓           ↓           ↓
┌──────────────┬──────────────┬──────────────────┐
│  PostgreSQL  │    Neo4j     │    Both DBs      │
│  + pgvector  │  + Graphiti  │                  │
└──────────────┴──────────────┴──────────────────┘
```

### RAG Variants

1. **Naive RAG**: 
   - Query → Embedding → Vector Search → Top-K Chunks → LLM Generation
   - Simple, fast, good baseline

2. **KG-RAG**:
   - Query → Entity Extraction → Graph Traversal → Subgraph → LLM Generation
   - Handles multi-hop reasoning, captures relationships

3. **Hybrid RAG**:
   - Query → [Vector Search || Graph Traversal] → Fusion → LLM Generation
   - Combines strengths of both approaches

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed technical documentation.

## 📊 Evaluation Methodology

### Evaluation Dimensions

Each answer is scored by an LLM evaluator on a 1-10 scale:

| Dimension | Description |
|-----------|-------------|
| Correctness | Factual accuracy compared to ground truth |
| Completeness | Coverage of all answer aspects |
| Relevance | Direct addressing of the question |
| Faithfulness | Only using information from retrieved context |
| Clarity | Structure and readability |

### Benchmark Datasets

Supported datasets:
- **HotpotQA**: Bridge and comparison questions
- **WikiMultiHopQA**: Wikipedia-based multi-hop QA
- **MultiHop-RAG**: Designed for RAG evaluation

### Output Format

**answers.json**:
```json
{
  "question_id": "hotpot_001",
  "question": "When was the author of 'Foundation' born?",
  "ground_truth": "January 2, 1920",
  "naive_rag": "Isaac Asimov was born in 1920.",
  "kg_rag": "Isaac Asimov, author of Foundation, was born on January 2, 1920.",
  "hybrid_rag": "The author of 'Foundation', Isaac Asimov, was born on January 2, 1920.",
  "metadata": {
    "naive_chunks": 5,
    "kg_entities": 3,
    "latencies": {...}
  }
}
```

**scores.json**:
```json
{
  "question_id": "hotpot_001",
  "naive_rag_scores": {
    "correctness": 8,
    "correctness_justification": "Correct year but missing exact date",
    "completeness": 7,
    "relevance": 9,
    "faithfulness": 10,
    "clarity": 9
  },
  "kg_rag_scores": {...},
  "hybrid_rag_scores": {...}
}
```

## 📈 Analysis & Visualization

### Statistical Analysis

The system provides:
- Summary statistics (mean, median, std dev) per dimension
- Paired statistical tests (t-test, Wilcoxon) between variants
- Correlation analysis between dimensions
- Question-type breakdown

### Visualizations

Generated plots:
- **Box plots**: Score distributions by dimension
- **Radar charts**: Comparative performance across dimensions
- **Bar charts**: Average scores per variant
- **Heatmaps**: Correlation between metrics
- **Latency comparisons**: Performance analysis

Example command:
```bash
python -m src.analysis.visualizations \
    --scores ./benchmarks/results/scores.json \
    --output-dir ./benchmarks/results/figures \
    --formats png pdf
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/test_rag_variants/

# Run integration tests
pytest tests/ -m integration
```

## 🐳 Docker Deployment

### Start All Services

```bash
docker-compose up -d
```

### Service Health Checks

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f neo4j

# Access Neo4j browser
open http://localhost:7474
```

### Stop Services

```bash
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v
```

## 📝 Development Workflow

### Adding a New RAG Variant

1. Create new file in `src/rag_variants/`
2. Inherit from `BaseRAG` class
3. Implement `retrieve()` and `generate()` methods
4. Register in orchestrator
5. Add tests

### Adding a New Benchmark Dataset

1. Create loader in `src/evaluation/benchmark_loader.py`
2. Implement dataset-specific parsing
3. Add to configuration options
4. Update documentation

### Custom Evaluation Metrics

1. Add dimension to `evaluation/models.py`
2. Update scoring prompts in `evaluation/scorer.py`
3. Extend analysis in `analysis/statistics.py`
4. Add visualization support

## 🔍 Troubleshooting

### Common Issues

**PostgreSQL connection refused**:
```bash
# Check if service is running
docker-compose ps postgres

# Restart service
docker-compose restart postgres
```

**Neo4j out of memory**:
```yaml
# Increase memory in docker-compose.yml
NEO4J_dbms_memory_heap_max__size: 4G
```

**Embedding generation slow**:
- Use batch processing
- Switch to local Ollama embeddings
- Reduce chunk size

**LLM rate limiting**:
- Add retry logic (already implemented)
- Use Ollama for testing
- Reduce concurrent requests

## 📚 Documentation

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) - High-level vision and goals
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical architecture details
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Development roadmap
- [TASKS.md](./TASKS.md) - Task tracking and progress

## 🤝 Contributing

1. Review [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
2. Pick a task from [TASKS.md](./TASKS.md)
3. Create a feature branch
4. Write tests
5. Submit PR with clear description

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Inspired by Cole Medin's Agentic RAG work
- Built with Pydantic AI framework
- Uses Graphiti for knowledge graphs
- Benchmark datasets from research community

## 📞 Support

- **Issues**: Open a GitHub issue
- **Questions**: Start a discussion
- **Documentation**: Check the docs/ folder

---

**Status**: 🚧 In Planning/Development

**Current Phase**: Planning & Architecture Complete

**Next Steps**: Begin Phase 1 implementation (Foundation & Infrastructure Setup)


## frequent commands

```bash
#  reset and ingest --subset
echo y | uv run python cli.py reset; uv run python cli.py ingest .\data\big_tech_docs

# all
uv run python cli.py reset; uv run python cli.py ingest .\data\datasets 

# evaluate 10 questions
uv run python cli.py evaluate --num-questions 10 --dataset factual_questions --output-dir .\benchmarks\factual_results

# analyze results
uv run python cli.py analyze .\benchmarks\factual_results\eval_*.json


## env  related
make clean
make setup
mkae

```


