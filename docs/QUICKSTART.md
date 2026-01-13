# Quick Start Guide

Get the RAG benchmarking system running in 10 minutes.

## Prerequisites

- Python 3.11+
- [UV](https://github.com/astral-sh/uv) (recommended) or pip
- Docker & Docker Compose
- 8GB+ RAM
- Gemini/OpenAI API key (or use Ollama locally)

## Installation

### 1. Install UV (1 min)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Setup Environment (2 min)

```bash
# Navigate to project
cd naive-rag-kg-rag

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync --all-extras
```

### 3. Configure (2 min)

```bash
# Copy template
cp .env.example .env

# Edit .env with your values
```

Minimum `.env`:
```bash
# Database
POSTGRES_PASSWORD=mysecurepassword
NEO4J_PASSWORD=neo4jpassword

# LLM
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-flash
LLM_API_KEY=your_gemini_api_key

# Embeddings
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL_NAME=text-embedding-004
EMBEDDING_API_KEY=your_gemini_api_key
```

### 4. Start Services (2 min)

```bash
# Start databases
docker-compose up -d

# Verify services are healthy
docker-compose ps

# Initialize databases
uv run python -m src.utils.db init
uv run python -m src.utils.graph init

# Verify complete setup
uv run python setup.py
```

### 5. Test System (3 min)

```bash
# Ingest sample documents
uv run python cli.py ingest ./data/big_tech_docs

# Run small evaluation
uv run python cli.py evaluate --num-questions 5 --dataset big_tech_curated

# View results
uv run python cli.py analyze ./benchmarks/runs/*/eval_*.json
```

## Common Commands

```bash
# Reset and ingest
uv run python cli.py reset
uv run python cli.py ingest ./data/big_tech_docs

# Run evaluation
uv run python cli.py evaluate --num-questions -1 --dataset big_tech_curated \
    --output-dir ./benchmarks/runs/my_run

# Analyze results
uv run python cli.py analyze ./benchmarks/runs/my_run/eval_*.json

# Get help
uv run python cli.py --help
```

## Troubleshooting

**Services not starting**:
```bash
docker-compose down -v
docker-compose up -d
```

**Database connection issues**:
```bash
uv run python setup.py
```

**Import errors**:
```bash
uv sync --all-extras
```

## Next Steps

- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for Docker details
- See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for project vision
