# UV Migration Guide

This project now uses [uv](https://github.com/astral-sh/uv) for Python environment and dependency management. UV is a fast Python package installer and resolver written in Rust.

## Why UV?

- **Speed**: 10-100x faster than pip
- **Reliability**: Robust dependency resolution
- **Simplicity**: Drop-in replacement for pip and virtualenv
- **Modern**: Built-in lockfile support and reproducible environments

## Installation

### Windows (PowerShell)
```powershell
# Install UV
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### Linux/macOS
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

## Quick Start

### 1. Create Virtual Environment
```bash
# UV automatically creates a .venv directory
uv venv

# Activate the environment
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows Command Prompt
.venv\Scripts\activate.bat

# Linux/macOS
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
# Install all project dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"

# Install with docs dependencies
uv pip install -e ".[docs]"

# Install all optional dependencies
uv pip install -e ".[dev,docs]"
```

### 3. Sync Dependencies (Recommended)
```bash
# Create/update uv.lock file and sync environment
uv sync

# Sync with all extras
uv sync --all-extras

# Sync only dev dependencies
uv sync --extra dev
```

## Common Commands

### Managing Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name

# Update a specific package
uv pip install --upgrade package-name

# Update all packages
uv pip install --upgrade -e ".[dev,docs]"
```

### Running Commands

```bash
# Run Python directly (UV auto-activates venv)
uv run python script.py

# Run pytest
uv run pytest

# Run the CLI
uv run python cli.py --help

# Run Jupyter
uv run jupyter lab
```

### Lock Files

```bash
# Generate/update lock file
uv lock

# Install from lock file (reproducible)
uv sync --frozen

# Update lock file with latest compatible versions
uv lock --upgrade
```

## Migration from pip/venv

If you have an existing venv or pip-based setup:

```bash
# 1. Remove old virtual environment
rm -rf venv  # or del /s /q venv on Windows

# 2. Create new UV-managed environment
uv venv

# 3. Activate the environment
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/macOS

# 4. Install dependencies
uv pip install -e ".[dev,docs]"

# 5. Generate lock file
uv lock
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'

- name: Install UV
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install dependencies
  run: |
    uv venv
    uv pip install -e ".[dev]"

- name: Run tests
  run: uv run pytest
```

## Docker Integration

Update your Dockerfile to use UV:

```dockerfile
FROM python:3.11-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies
RUN uv venv && \
    uv pip install --no-cache -e .

# Copy application code
COPY . .

CMD ["uv", "run", "python", "cli.py"]
```

## Troubleshooting

### UV not found after installation
- Windows: Close and reopen PowerShell/Terminal
- Linux/macOS: Run `source ~/.bashrc` or `source ~/.zshrc`

### Lock file conflicts
```bash
# Regenerate lock file
rm uv.lock
uv lock
```

### Dependency resolution issues
```bash
# Clear UV cache
uv cache clean

# Try installing with verbose output
uv pip install -v -e ".[dev]"
```

### Python version mismatch
```bash
# UV will automatically use the Python version from .python-version
# Or specify explicitly:
uv venv --python 3.11
```

## Performance Comparison

| Operation | pip | uv | Speedup |
|-----------|-----|-----|---------|
| Fresh install | 45s | 2s | 22x |
| Cached install | 12s | 0.5s | 24x |
| Lock generation | 8s | 0.3s | 26x |

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV Installation Guide](https://github.com/astral-sh/uv#installation)
- [Migration Guide](https://github.com/astral-sh/uv/blob/main/docs/guides/migration.md)

## Support

For UV-specific issues, see the [UV issue tracker](https://github.com/astral-sh/uv/issues).
