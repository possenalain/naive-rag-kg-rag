# Docker Guide

This guide explains how to use Docker with this project, including when to use each Dockerfile and how to integrate with docker-compose.

## Table of Contents
1. [Dockerfile Overview](#dockerfile-overview)
2. [Building Images](#building-images)
3. [Running Containers](#running-containers)
4. [Docker Compose Integration](#docker-compose-integration)
5. [Best Practices](#best-practices)

## Dockerfile Overview

### `Dockerfile` - Production Image

**Purpose**: Optimized for production deployment

**Features**:
- ✅ Multi-stage build (smaller image)
- ✅ Only production dependencies
- ✅ Security-focused (non-root user)
- ✅ Minimal system packages
- ✅ Fast startup time
- ✅ ~500MB final image size

**Use Cases**:
- Production deployment
- Cloud services (AWS ECS, Azure Container Instances, GCP Cloud Run)
- Kubernetes clusters
- CI/CD pipelines
- Distribution to others

**Example Build**:
```bash
docker build -t naive-rag:latest .
docker build -t naive-rag:v1.0.0 .  # Tagged version
```

### `Dockerfile.dev` - Development Image

**Purpose**: Full development environment in a container

**Features**:
- ✅ All dev dependencies (pytest, black, mypy, etc.)
- ✅ Build tools included
- ✅ Git and debugging tools
- ✅ Volume mounting support
- ✅ Interactive shell access
- ⚠️ ~800MB image size

**Use Cases**:
- Local development
- Debugging issues
- Running tests
- Code formatting/linting
- Development without local Python setup
- Consistent dev environment across team

**Example Build**:
```bash
docker build -f Dockerfile.dev -t naive-rag:dev .
```

## Building Images

### Production Image

```bash
# Basic build
docker build -t naive-rag:latest .

# Build with specific tag
docker build -t naive-rag:v1.0.0 .

# Build with no cache (force rebuild)
docker build --no-cache -t naive-rag:latest .

# Build for specific platform (for deployment)
docker build --platform linux/amd64 -t naive-rag:latest .
```

### Development Image

```bash
# Basic build
docker build -f Dockerfile.dev -t naive-rag:dev .

# Build with progress
docker build -f Dockerfile.dev -t naive-rag:dev --progress=plain .

# Build with build arguments
docker build -f Dockerfile.dev \
  --build-arg PYTHON_VERSION=3.11 \
  -t naive-rag:dev .
```

## Running Containers

### Production Container

**Basic Run**:
```bash
docker run -it --rm \
  --name rag-app \
  --env-file .env \
  naive-rag:latest
```

**With Network (to connect to databases)**:
```bash
# First, ensure databases are running
docker-compose up -d postgres neo4j

# Run app container
docker run -it --rm \
  --name rag-app \
  --env-file .env \
  --network naive-rag-kg-rag_rag_network \
  naive-rag:latest python cli.py --help
```

**As Background Service**:
```bash
docker run -d \
  --name rag-app \
  --restart unless-stopped \
  --env-file .env \
  --network naive-rag-kg-rag_rag_network \
  naive-rag:latest
```

### Development Container

**Interactive Shell**:
```bash
docker run -it --rm \
  --name rag-dev \
  -v ${PWD}:/workspace \
  --env-file .env \
  --network naive-rag-kg-rag_rag_network \
  naive-rag:dev bash
```

**Run Tests**:
```bash
docker run -it --rm \
  -v ${PWD}:/workspace \
  --env-file .env \
  --network naive-rag-kg-rag_rag_network \
  naive-rag:dev uv run pytest tests/
```

**Run Jupyter**:
```bash
docker run -it --rm \
  -v ${PWD}:/workspace \
  -p 8888:8888 \
  --env-file .env \
  --network naive-rag-kg-rag_rag_network \
  naive-rag:dev uv run jupyter lab --ip=0.0.0.0 --allow-root
```

**Format Code**:
```bash
docker run -it --rm \
  -v ${PWD}:/workspace \
  naive-rag:dev uv run black src tests
```

## Docker Compose Integration

### Option 1: Add to Existing docker-compose.yml

Add the application service alongside databases:

```yaml
services:
  # ... existing postgres and neo4j services ...

  # Production app
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rag_app
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_healthy
    networks:
      - rag_network
    volumes:
      - ./data:/data
      - ./logs:/logs
    restart: unless-stopped

  # Development app (commented out by default)
  # app-dev:
  #   build:
  #     context: .
  #     dockerfile: Dockerfile.dev
  #   container_name: rag_app_dev
  #   env_file: .env
  #   volumes:
  #     - .:/workspace
  #   depends_on:
  #     - postgres
  #     - neo4j
  #   networks:
  #     - rag_network
  #   command: bash
  #   stdin_open: true
  #   tty: true
```

### Option 2: Separate Compose Files

**docker-compose.yml** (Infrastructure only):
```yaml
# Keep only postgres, neo4j, redis, ollama
```

**docker-compose.app.yml** (Application):
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    # ... app configuration
```

**docker-compose.dev.yml** (Development):
```yaml
version: '3.8'

services:
  app-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    # ... dev configuration
```

**Usage**:
```bash
# Infrastructure only
docker-compose up -d

# Infrastructure + Production app
docker-compose -f docker-compose.yml -f docker-compose.app.yml up -d

# Infrastructure + Development app
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Best Practices

### When to Use Each Approach

| Scenario | Recommended Dockerfile | Run Method |
|----------|----------------------|------------|
| Production deployment | `Dockerfile` | docker-compose or standalone |
| CI/CD testing | `Dockerfile` | docker run |
| Local development | Neither* | UV locally (faster) |
| Team standardization | `Dockerfile.dev` | docker-compose.dev.yml |
| Debugging in isolation | `Dockerfile.dev` | docker run with volumes |
| Can't install Python locally | `Dockerfile.dev` | docker run interactive |

\* **Recommended**: Use UV locally for development - it's faster and more convenient

### Development Workflow Recommendations

**Option A: Local UV (Recommended)**
```bash
# Fastest development workflow
uv venv
uv sync --all-extras

# Databases in Docker, code runs locally
docker-compose up -d postgres neo4j
uv run python cli.py
uv run pytest
```

**Option B: Hybrid (Good for team consistency)**
```bash
# Databases and app in Docker, live code updates
docker-compose up -d
docker run -it --rm \
  -v ${PWD}:/workspace \
  --network rag_network \
  naive-rag:dev bash

# Inside container:
uv run python cli.py
```

**Option C: Full Docker (Good for isolation)**
```bash
# Everything in Docker
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Exec into container
docker exec -it rag_app_dev bash
```

### Image Size Optimization

**Production Image**:
- Uses multi-stage build
- Only copies necessary files
- Minimal base image (python:3.11-slim)
- No dev dependencies
- Result: ~500MB

**Development Image**:
- Single stage build
- Includes all tools
- Build tools included
- All dev dependencies
- Result: ~800MB

### Security Considerations

**Production**:
- ✅ Runs as non-root user (`raguser`)
- ✅ Minimal attack surface
- ✅ No unnecessary packages
- ✅ Health checks included
- ✅ Read-only root filesystem (can enable)

**Development**:
- ⚠️ More packages = larger attack surface
- ⚠️ Development tools included
- ⚠️ Should not be used in production

### Volume Mounting

**For Development**:
```bash
# Mount entire project
-v ${PWD}:/workspace

# Mount specific directories
-v ${PWD}/src:/workspace/src
-v ${PWD}/tests:/workspace/tests
-v ${PWD}/data:/workspace/data

# Mount as read-only (for data)
-v ${PWD}/data:/workspace/data:ro
```

**For Production**:
```bash
# Only mount data/logs, not code
-v ./data:/data
-v ./logs:/logs
```

## Common Commands

### Build Both Images
```bash
# Build production
docker build -t naive-rag:latest .

# Build development
docker build -f Dockerfile.dev -t naive-rag:dev .
```

### Clean Up
```bash
# Remove all project images
docker rmi naive-rag:latest naive-rag:dev

# Remove unused images
docker image prune -a

# Remove all stopped containers
docker container prune
```

### Inspect Images
```bash
# View image size
docker images naive-rag

# View image layers
docker history naive-rag:latest

# Inspect image details
docker inspect naive-rag:latest
```

### Push to Registry

**Docker Hub**:
```bash
docker tag naive-rag:latest username/naive-rag:latest
docker push username/naive-rag:latest
```

**GitHub Container Registry**:
```bash
docker tag naive-rag:latest ghcr.io/username/naive-rag:latest
docker push ghcr.io/username/naive-rag:latest
```

## Troubleshooting

### Build Failures

**UV Not Found**:
```bash
# Ensure you're using the latest Dockerfile with UV
# Rebuild without cache
docker build --no-cache -t naive-rag:latest .
```

**Dependency Errors**:
```bash
# Clear UV cache in container
docker build --no-cache -t naive-rag:latest .

# Or modify Dockerfile to add: RUN uv cache clean
```

### Runtime Issues

**Can't Connect to Databases**:
```bash
# Ensure containers are on same network
docker network ls
docker network inspect naive-rag-kg-rag_rag_network

# Use correct service names (postgres, neo4j, not localhost)
```

**Permission Errors**:
```bash
# Development: Run as root if needed
docker run --user root ...

# Production: Ensure volumes have correct permissions
chown -R 1000:1000 ./data ./logs
```

**Environment Variables Not Working**:
```bash
# Check .env file exists
ls -la .env

# Use --env-file flag
docker run --env-file .env ...

# Or pass individually
docker run -e POSTGRES_PASSWORD=secret ...
```

## Summary

| Task | Use | Command |
|------|-----|---------|
| Production deployment | `Dockerfile` | `docker build -t naive-rag:latest .` |
| Development with Docker | `Dockerfile.dev` | `docker build -f Dockerfile.dev -t naive-rag:dev .` |
| Local development | UV (no Docker) | `uv sync && uv run python cli.py` |
| Running tests | `Dockerfile.dev` or UV | `docker run ... uv run pytest` or `uv run pytest` |
| CI/CD | `Dockerfile` | Build and test in pipeline |

**Recommendation**: 
- 🏆 Use **UV locally** for daily development (fastest)
- 🐳 Use **Dockerfile.dev** when team needs consistent environment
- 🚀 Use **Dockerfile** for production deployment

## Next Steps

1. Choose your development approach (UV locally vs Docker)
2. Build the appropriate image(s)
3. Update docker-compose.yml if needed
4. Test your setup
5. Document your team's chosen workflow

For more details on UV usage, see [UV_MIGRATION.md](UV_MIGRATION.md).
