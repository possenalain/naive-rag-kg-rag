# Multi-stage build using UV for fast dependency installation
FROM python:3.11-slim as builder

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY .python-version .
COPY README.md .

# Copy source code
COPY src/ src/
COPY config/ config/

# Create virtual environment and install dependencies
RUN uv venv && \
    uv pip install --no-cache -e .

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

# Copy application code
COPY --chown=raguser:raguser src/ src/
COPY --chown=raguser:raguser config/ config/
COPY --chown=raguser:raguser cli.py .

# Switch to non-root user
USER raguser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncpg; import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "cli.py", "--help"]
