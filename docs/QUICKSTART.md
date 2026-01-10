# Quick Start Guide

Get up and running with the RAG benchmarking system in under 10 minutes!

## Prerequisites Check

Before you begin, ensure you have:
- ✅ Python 3.11 or higher
- ✅ [UV](https://github.com/astral-sh/uv) - Fast Python package installer (recommended)
- ✅ Docker and Docker Compose
- ✅ At least 8GB RAM
- ✅ API key for Gemini (or OpenAI, or plan to use Ollama)

## Step-by-Step Setup

### 1. Install UV (1 minute)

UV is a fast Python package installer that's 10-100x faster than pip.

**Windows PowerShell**:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verify Installation**:
```bash
uv --version
```

### 2. Environment Setup (1 minute)

```bash
# Navigate to project directory
cd naive-rag-kg-rag

# Create virtual environment with UV
uv venv

# Activate the environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Windows Command Prompt:
.venv\Scripts\activate.bat

# Linux/Mac:
source .venv/bin/activate

# Install all dependencies (this is fast with UV!)
uv sync --all-extras
```

<details>
<summary>Alternative: Traditional pip method (slower)</summary>

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
</details>

### 3. Configure Environment (2 minutes)

```bash
# Copy environment template
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env file with your actual values
# Minimum required:
# - POSTGRES_PASSWORD=your_secure_password
# - NEO4J_PASSWORD=your_neo4j_password  
# - LLM_API_KEY=your_gemini_or_openai_key
# - EMBEDDING_API_KEY=your_api_key
```

**Quick .env setup for Gemini**:
```bash
# Database
POSTGRES_PASSWORD=mysecurepassword
NEO4J_PASSWORD=neo4jpassword

# LLM
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-flash  # Use flash for cost savings
LLM_API_KEY=YOUR_GEMINI_API_KEY

# Embeddings
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL_NAME=text-embedding-004
EMBEDDING_API_KEY=YOUR_GEMINI_API_KEY
```

### 4. Start Infrastructure (3 minutes)

```bash
# Start PostgreSQL and Neo4j
docker-compose up -d

# Wait for services to be healthy (watch until all show 'healthy')
docker-compose ps

# Should see:
# rag_postgres    running (healthy)
# rag_neo4j       running (healthy)
```

**Verify services**:
```bash
# PostgreSQL
docker exec rag_postgres pg_isready -U raguser

# Neo4j browser (open in browser)
# http://localhost:7474
# Login: neo4j / <your NEO4J_PASSWORD>
```

### 5. Initialize Databases (1 minute)

The PostgreSQL schema is automatically initialized on first start via `sql/schema.sql`.

To verify:
```bash
# Check PostgreSQL
docker exec -it rag_postgres psql -U raguser -d rag_benchmark -c "\dt"

# Should show: documents, chunks, benchmark_questions, evaluations, scores
```

### 6. Quick Test (2 minutes)

Create a test script to verify everything works:

```python
# test_setup.py
import asyncio
import asyncpg
from neo4j import GraphDatabase

async def test_postgres():
    conn = await asyncpg.connect(
        "postgresql://raguser:your_password@localhost:5432/rag_benchmark"
    )
    result = await conn.fetchval("SELECT COUNT(*) FROM documents")
    print(f"✅ PostgreSQL connected! Documents: {result}")
    await conn.close()

def test_neo4j():
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "your_password")
    )
    with driver.session() as session:
        result = session.run("RETURN 1 as num")
        print(f"✅ Neo4j connected! Test query: {result.single()['num']}")
    driver.close()

async def main():
    await test_postgres()
    test_neo4j()
    print("\n🎉 All systems operational!")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
# With UV:
uv run python test_setup.py

# Or with activated venv:
python test_setup.py
```

## Next Steps

### Option A: Ingest Sample Documents (Not Yet Implemented)

```bash
# Once implementation is complete, you'll run:
# With UV:
uv run python -m src.ingestion.pipeline \
    --input-dir ./data/documents \
    --build-graph

# Or with activated venv:
python -m src.ingestion.pipeline --input-dir ./data/documents --build-graph
```

### Option B: Run Sample Evaluation (Not Yet Implemented)

```bash
# Once implementation is complete:
# With UV:
uv run python -m src.evaluation.orchestrator --dataset hotpotqa

# Or with activated venv:
python -m src.evaluation.orchestrator --dataset hotpotqa
```
python -m src.evaluation.orchestrator \
    --dataset hotpotqa \
    --num-questions 10 \
    --output ./benchmarks/results
```

### Option C: Start Development

Pick a task from [TASKS.md](./TASKS.md) and start implementing!

Recommended starting points:
1. **Configuration Management** (`config/settings.py`)
2. **Database Utilities** (`src/utils/db.py`)
3. **Document Loader** (`src/ingestion/loader.py`)

## UV Quick Reference

```bash
# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Run scripts without activating venv
uv run python script.py
uv run pytest

# Update all dependencies
uv sync --upgrade

# See all UV commands
uv --help
```

For more UV details, see [UV_MIGRATION.md](UV_MIGRATION.md).

## Common Issues

### Port Already in Use

```bash
# PostgreSQL port 5432
netstat -ano | findstr :5432  # Windows
lsof -i :5432  # Linux/Mac

# Neo4j port 7687
netstat -ano | findstr :7687  # Windows
lsof -i :7687  # Linux/Mac

# Kill the process or change port in docker-compose.yml
```

### Docker Services Won't Start

```bash
# View logs
docker-compose logs postgres
docker-compose logs neo4j

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

### Python Version Issues

```bash
# Check Python version
python --version  # Should be 3.11+

# If using multiple Python versions
python3.11 -m venv venv
```

### Import Errors

```bash
# Ensure virtual environment is activated
# You should see (venv) in your terminal

# Reinstall requirements
pip install --upgrade pip
pip install -r requirements.txt
```

## Development Workflow

### Daily Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Run tests
pytest

# 4. Work on features

# 5. When done
docker-compose stop
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_ingestion/

# With coverage
pytest --cov=src --cov-report=html

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Lint
flake8 src/
pylint src/

# Type checking
mypy src/
```

## Quick Reference

### Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose stop

# View logs
docker-compose logs -f

# Restart service
docker-compose restart postgres

# Remove everything (including data!)
docker-compose down -v

# Execute command in container
docker exec -it rag_postgres psql -U raguser -d rag_benchmark
```

### Database Access

```bash
# PostgreSQL CLI
docker exec -it rag_postgres psql -U raguser -d rag_benchmark

# Neo4j Browser
open http://localhost:7474

# Redis CLI (if using cache)
docker exec -it rag_redis redis-cli
```

## Need Help?

1. Check [README.md](./README.md) for comprehensive documentation
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details
3. See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for development roadmap
4. Check [TASKS.md](./TASKS.md) for current progress

## Cost Optimization Tips

### During Development

1. **Use Gemini Flash** instead of Pro:
   ```bash
   LLM_MODEL_NAME=gemini-1.5-flash
   ```

2. **Use Local Embeddings** with Ollama:
   ```bash
   # Start Ollama
   docker-compose up -d ollama
   
   # Pull embedding model
   docker exec rag_ollama ollama pull nomic-embed-text
   
   # Update .env
   EMBEDDING_PROVIDER=ollama
   EMBEDDING_MODEL_NAME=nomic-embed-text
   EMBEDDING_BASE_URL=http://localhost:11434
   ```

3. **Enable Caching**:
   ```bash
   ENABLE_EMBEDDING_CACHE=true
   USE_CACHE=true
   ```

4. **Use Small Test Sets** during development:
   ```bash
   BENCHMARK_NUM_QUESTIONS=10  # Instead of 50
   ```

### For Production Runs

1. **Batch Processing**: Process in batches to avoid rate limits
2. **Async Operations**: Leverage async for parallel processing
3. **Retry Logic**: Already implemented to handle transient failures
4. **Monitor Costs**: Track token usage and API calls

## Success! 🎉

You should now have:
- ✅ Virtual environment activated
- ✅ Dependencies installed
- ✅ PostgreSQL running with schema
- ✅ Neo4j running and accessible
- ✅ Environment configured
- ✅ Ready to start development!

**Next**: Review [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) and pick your first task!
