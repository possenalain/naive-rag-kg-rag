# ============================================================================
# PRODUCTION DOCKERFILE
# ============================================================================
# Purpose: Optimized production image for deployment
# Size: ~500MB (multi-stage build)
# Use when: Deploying to production, cloud services, or distribution
# 
# Build: docker build -t naive-rag:latest .
# Run:   docker run -it --rm --env-file .env naive-rag:latest
#
# Features:
# - Multi-stage build (smaller image)
# - Only production dependencies
# - Non-root user for security
# - Minimal attack surface
# - Fast startup time
#
# See docs/DOCKER_GUIDE.md for complete documentation
# ============================================================================

# Multi-stage build using UV for fast dependency installation
FROM python:3.11-slim AS builder

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables for faster builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock .python-version README.md ./

# Install dependencies using the lock file (much faster)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source code and install project
COPY src/ src/
COPY config/ config/
COPY cli.py .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 raguser && \
    mkdir -p /app /data /logs && \
    chown -R raguser:raguser /app /data /logs

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=raguser:raguser /app/.venv /app/.venv

# Copy application code including new agent module
COPY --chown=raguser:raguser src/ src/
COPY --chown=raguser:raguser config/ config/
COPY --chown=raguser:raguser cli.py .
COPY --chown=raguser:raguser benchmarks/datasets/ benchmarks/datasets/

# Switch to non-root user
USER raguser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Create cache directories for embeddings and models
RUN mkdir -p /app/cache/embeddings /app/cache/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncpg; import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "cli.py", "--help"]
