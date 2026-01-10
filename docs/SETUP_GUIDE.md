# Complete Setup Guide with UV

This guide walks you through setting up the RAG benchmarking project using UV, the modern Python package manager.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installing UV](#installing-uv)
3. [Project Setup](#project-setup)
4. [Development Workflow](#development-workflow)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- **Python 3.11+**: Check with `python --version`
- **Docker Desktop**: For PostgreSQL and Neo4j
- **Git**: For version control
- **PowerShell 5.1+** (Windows) or **Bash** (Linux/macOS)

### API Keys
You'll need at least one of:
- Google Gemini API key (recommended for getting started)
- OpenAI API key
- Anthropic API key

## Installing UV

### Windows

**Option 1: PowerShell (Recommended)**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Option 2: Using pipx**
```powershell
pipx install uv
```

**Verify Installation**:
```powershell
uv --version
```

### Linux/macOS

**Option 1: Shell Script (Recommended)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Option 2: Using pip**
```bash
pip install uv
```

**Verify Installation**:
```bash
uv --version
```

### Update UV
```bash
# Update to latest version
uv self update
```

## Project Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd naive-rag-kg-rag
```

### 2. Create Virtual Environment

UV automatically creates a `.venv` directory:

```bash
# Create virtual environment
uv venv

# UV will use the Python version from .python-version file
```

### 3. Activate Virtual Environment

**Windows PowerShell**:
```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**:
```cmd
.venv\Scripts\activate.bat
```

**Linux/macOS**:
```bash
source .venv/bin/activate
```

**Verify Activation**:
```bash
which python  # Linux/macOS
where python  # Windows
```

### 4. Install Dependencies

**Option A: Using sync (Recommended)**
```bash
# Install all dependencies including dev and docs
uv sync --all-extras

# This will:
# 1. Read pyproject.toml
# 2. Create/update uv.lock
# 3. Install all packages in locked versions
```

**Option B: Using pip install**
```bash
# Install production dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"

# Install with all extras
uv pip install -e ".[dev,docs]"
```

### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env  # Linux/macOS
copy .env.example .env  # Windows

# Edit .env file
# Add your API keys and database passwords
```

**Minimal .env setup**:
```env
# Database
POSTGRES_PASSWORD=your_secure_password
NEO4J_PASSWORD=your_neo4j_password

# LLM
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-flash
LLM_API_KEY=your_gemini_api_key

# Embeddings
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL_NAME=text-embedding-004
EMBEDDING_API_KEY=your_gemini_api_key
```

### 6. Start Infrastructure

```bash
# Start PostgreSQL and Neo4j
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Check logs if needed
docker-compose logs -f postgres
docker-compose logs -f neo4j
```

### 7. Verify Setup

```bash
# Check Python environment
uv run python --version

# List installed packages
uv pip list

# Test database connections (if setup.py is configured)
uv run python setup.py
```

## Development Workflow

### Running Commands with UV

UV provides multiple ways to run commands:

**Option 1: UV run (no activation needed)**
```bash
# Run Python scripts directly
uv run python cli.py --help

# Run pytest
uv run pytest tests/

# Run Jupyter
uv run jupyter lab
```

**Option 2: Activated virtual environment**
```bash
# Activate first
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\Activate.ps1  # Windows

# Then run normally
python cli.py --help
pytest tests/
jupyter lab
```

### Managing Dependencies

**Add New Package**:
```bash
# Add production dependency
uv add requests

# Add dev dependency
uv add --dev pytest-xdist

# This updates pyproject.toml and uv.lock
```

**Remove Package**:
```bash
uv remove package-name
```

**Update Packages**:
```bash
# Update specific package
uv pip install --upgrade package-name

# Update all packages to latest compatible versions
uv lock --upgrade
uv sync
```

**View Dependency Tree**:
```bash
uv pip list
uv pip show package-name
```

### Using Helper Scripts

**Windows (PowerShell)**:
```powershell
# Complete setup
.\make.ps1 setup

# Run tests
.\make.ps1 test

# Format code
.\make.ps1 format

# Run linters
.\make.ps1 lint

# Start Docker services
.\make.ps1 docker-up

# See all commands
.\make.ps1 help
```

**Linux/macOS (Makefile)**:
```bash
# Complete setup
make setup

# Run tests
make test

# Format code
make format

# Run linters
make lint

# Start Docker services
make docker-up

# See all commands
make help
```

### Code Quality

```bash
# Format code
uv run black src tests
uv run isort src tests

# Check formatting without changes
uv run black --check src tests
uv run isort --check-only src tests

# Lint code
uv run flake8 src tests

# Type checking
uv run mypy src

# Or use helper script
.\make.ps1 format  # Windows
make format        # Linux/macOS
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_ingestion/test_loader.py

# Run with verbose output
uv run pytest tests/ -v

# Or use helper script
.\make.ps1 test      # Windows
make test            # Linux/macOS
```

### Jupyter Notebooks

```bash
# Start Jupyter Lab
uv run jupyter lab notebooks/

# Or with activated venv
jupyter lab notebooks/
```

## Troubleshooting

### UV Not Found After Installation

**Windows**:
1. Close and reopen PowerShell/Terminal
2. Or manually add to PATH: `$env:Path += ";$env:USERPROFILE\.cargo\bin"`

**Linux/macOS**:
```bash
# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc

# Or manually add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

### Virtual Environment Issues

```bash
# Remove and recreate venv
rm -rf .venv  # Linux/macOS
Remove-Item -Recurse -Force .venv  # Windows

# Create new venv
uv venv

# Reinstall dependencies
uv sync --all-extras
```

### Dependency Conflicts

```bash
# Clear UV cache
uv cache clean

# Remove lockfile and regenerate
rm uv.lock  # Linux/macOS
Remove-Item uv.lock  # Windows

# Regenerate
uv lock
uv sync --all-extras
```

### Import Errors

```bash
# Ensure you're in the right directory
pwd  # Linux/macOS
Get-Location  # Windows

# Ensure virtual environment is activated
which python  # Should show .venv path

# Reinstall in editable mode
uv pip install -e .
```

### Docker Services Won't Start

```bash
# Check if ports are already in use
netstat -an | findstr :5432  # Windows
lsof -i :5432  # Linux/macOS

# View service logs
docker-compose logs postgres
docker-compose logs neo4j

# Restart services
docker-compose restart

# Full reset (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Performance Issues

UV is designed to be fast, but if you experience slowness:

```bash
# Use --no-cache for fresh installs
uv pip install --no-cache -e ".[dev]"

# Verify UV version (should be latest)
uv --version
uv self update

# Check disk space
df -h  # Linux/macOS
Get-PSDrive  # Windows
```

## Next Steps

After successful setup:

1. **Read the Documentation**:
   - [README.md](README.md) - Project overview
   - [QUICKSTART.md](QUICKSTART.md) - Quick start guide
   - [UV_MIGRATION.md](UV_MIGRATION.md) - UV usage details

2. **Run the Tutorial**:
   ```bash
   uv run jupyter lab notebooks/quickstart_tutorial.ipynb
   ```

3. **Start Development**:
   - Check [TASKS.md](TASKS.md) for implementation tasks
   - Run tests: `uv run pytest`
   - Start coding!

## Additional Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL with pgvector](https://github.com/pgvector/pgvector)
- [Neo4j Documentation](https://neo4j.com/docs/)

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Review the [UV documentation](https://github.com/astral-sh/uv)
3. Check project issues on GitHub
4. Ask in project discussions/chat

## Summary Commands

```bash
# Complete first-time setup
uv venv
uv sync --all-extras
cp .env.example .env
# Edit .env with your settings
docker-compose up -d

# Daily development
uv run python cli.py
uv run pytest
uv run jupyter lab

# Add dependencies
uv add package-name

# Update everything
uv lock --upgrade
uv sync

# Helper scripts (recommended)
.\make.ps1 help  # Windows
make help        # Linux/macOS
```
