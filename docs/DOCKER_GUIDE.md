# Docker Guide

## Dockerfiles

### `Dockerfile` - Production
- Multi-stage build (~500MB)
- Production dependencies only
- Non-root user for security
- Use for: Deployment, CI/CD

```bash
docker build -t naive-rag:latest .
```

### `Dockerfile.dev` - Development  
- Full dev dependencies (~800MB)
- Debugging and testing tools
- Use for: Local development

```bash
docker build -f Dockerfile.dev -t naive-rag:dev .
```

## Docker Compose

### Start Services

```bash
# Start PostgreSQL and Neo4j
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f neo4j
```

### Service Access

- **PostgreSQL**: localhost:5432
- **Neo4j Browser**: http://localhost:7474
- **Neo4j Bolt**: bolt://localhost:7687

### Stop Services

```bash
# Stop
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Running Application in Docker

### Production

```bash
# Run once
docker run --rm \
  --network naive-rag-kg-rag_default \
  --env-file .env \
  naive-rag:latest \
  python cli.py --help

# Interactive shell
docker run -it --rm \
  --network naive-rag-kg-rag_default \
  --env-file .env \
  naive-rag:latest \
  /bin/bash
```

### Development

```bash
# Mount code for live updates
docker run -it --rm \
  --network naive-rag-kg-rag_default \
  --env-file .env \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/tests:/app/tests \
  naive-rag:dev \
  /bin/bash
```

## Common Tasks

### Ingest Documents

```bash
docker run --rm \
  --network naive-rag-kg-rag_default \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  naive-rag:latest \
  python cli.py ingest /app/data/big_tech_docs
```

### Run Evaluation

```bash
docker run --rm \
  --network naive-rag-kg-rag_default \
  --env-file .env \
  -v $(pwd)/benchmarks:/app/benchmarks \
  naive-rag:latest \
  python cli.py evaluate --dataset big_tech_curated
```

### Run Tests

```bash
docker run --rm naive-rag:dev pytest
```

## Troubleshooting

**Connection issues**:
```bash
# Ensure services are on same network
docker network ls
docker inspect naive-rag-kg-rag_default
```

**Permission issues**:
```bash
# Application runs as non-root user (appuser)
# Ensure mounted volumes have correct permissions
chmod -R 755 ./data ./benchmarks
```

**Database connection**:
```bash
# Use service names, not localhost
POSTGRES_URL=postgresql://raguser:password@postgres:5432/rag_benchmark
NEO4J_URI=bolt://neo4j:7687
```

## Best Practices

1. **Use docker-compose** for local development
2. **Mount volumes** for data persistence
3. **Use .env file** for configuration
4. **Tag images** for version control
5. **Clean up** unused images regularly

```bash
# Clean up
docker system prune -a
docker volume prune
```
