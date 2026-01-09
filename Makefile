.PHONY: help install install-dev clean test lint format docker-up docker-down setup

# Default target
help:
	@echo "Available commands:"
	@echo "  make install        - Create venv and install dependencies with UV"
	@echo "  make install-dev    - Install with dev dependencies"
	@echo "  make clean          - Remove virtual environment and cache files"
	@echo "  make test           - Run tests with pytest"
	@echo "  make lint           - Run linters (flake8, mypy)"
	@echo "  make format         - Format code with black and isort"
	@echo "  make docker-up      - Start Docker services (PostgreSQL, Neo4j)"
	@echo "  make docker-down    - Stop Docker services"
	@echo "  make setup          - Complete setup (install + docker)"
	@echo "  make sync           - Sync dependencies from lockfile"
	@echo "  make update         - Update all dependencies"
	@echo "  make run-jupyter    - Start Jupyter Lab"

# Install UV if not present
check-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "UV not found. Installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}

# Create virtual environment and install dependencies
install: check-uv
	uv venv
	uv pip install -e .
	@echo "✅ Installation complete! Activate with: source .venv/bin/activate"

# Install with dev dependencies
install-dev: check-uv
	uv venv
	uv sync --all-extras
	@echo "✅ Dev installation complete!"

# Sync from lockfile
sync: check-uv
	uv sync --all-extras

# Update all dependencies
update: check-uv
	uv lock --upgrade
	uv sync --all-extras

# Clean build artifacts and cache
clean:
	rm -rf .venv
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned up!"

# Run tests
test:
	uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Run tests with coverage report
test-cov:
	uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run linters
lint:
	uv run flake8 src tests
	uv run mypy src
	@echo "✅ Linting complete!"

# Check code formatting
format-check:
	uv run black --check src tests
	uv run isort --check-only src tests

# Format code
format:
	uv run black src tests
	uv run isort src tests
	@echo "✅ Code formatted!"

# Start Docker services
docker-up:
	docker-compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	docker-compose ps
	@echo "✅ Docker services started!"

# Stop Docker services
docker-down:
	docker-compose down
	@echo "✅ Docker services stopped!"

# Reset Docker (with volume cleanup)
docker-reset:
	docker-compose down -v
	docker-compose up -d
	@echo "✅ Docker services reset!"

# Complete setup
setup: install-dev docker-up
	@echo "🎉 Setup complete! You're ready to go!"

# Run Jupyter Lab
run-jupyter:
	uv run jupyter lab notebooks/

# Run CLI help
run-cli:
	uv run python cli.py --help

# Quick development cycle
dev: format lint test
	@echo "✅ Development checks passed!"

# CI/CD simulation
ci: install-dev format-check lint test
	@echo "✅ CI checks passed!"

# Database initialization
init-db:
	docker exec -it rag_postgres psql -U raguser -d rag_benchmark -f /sql/schema.sql
	@echo "✅ Database initialized!"

# Show current environment
env-info:
	@echo "Python Environment Information:"
	@uv run python --version
	@echo "\nInstalled Packages:"
	@uv pip list

# Add a new dependency
add:
	@read -p "Package name: " pkg; \
	uv add $$pkg
	@echo "✅ Package added!"

# Add a dev dependency
add-dev:
	@read -p "Package name: " pkg; \
	uv add --dev $$pkg
	@echo "✅ Dev package added!"
