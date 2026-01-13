# Database Backups

Backup and restore PostgreSQL and Neo4j databases.

## Directory Structure

```
db/backups/
├── postgres_backup_YYYYMMDD_HHMMSS.sql
├── postgres_backup_YYYYMMDD_HHMMSS_metadata.json
├── neo4j_backup_YYYYMMDD_HHMMSS.cypher
└── neo4j_backup_YYYYMMDD_HHMMSS_metadata.json
```

## Usage

### Create Backup

```bash
python cli.py backup
python cli.py backup --name my_backup
python cli.py backup --postgres-only
python cli.py backup --neo4j-only
```

### Restore Backup

```bash
# List available backups
python cli.py restore --list-backups

# Restore both databases
python cli.py restore \
  --postgres-backup db/backups/postgres_backup_20260110.sql \
  --neo4j-backup db/backups/neo4j_backup_20260110.cypher

# Restore specific database
python cli.py restore --postgres-backup db/backups/postgres_backup_20260110.sql
python cli.py restore --neo4j-backup db/backups/neo4j_backup_20260110.cypher
```

## Backup Contents

**PostgreSQL (.sql)**:
- Schema + data
- Documents, chunks, embeddings
- Evaluation history

**Neo4j (.cypher)**:
- Nodes (entities, chunks, episodes)
- Relationships
- Properties and labels

**Metadata (.json)**:
- Timestamp
- Database statistics
- Version info

## Best Practices

```bash
# Backup before major changes
python cli.py backup --name before_experiment

# Backup before reset
python cli.py backup
python cli.py reset

# Test restore periodically
python cli.py restore --list-backups
```

## Recovery Examples

**Accidental deletion**:
```bash
python cli.py restore --list-backups  # Find latest
python cli.py restore --postgres-backup db/backups/postgres_backup_LATEST.sql
```

**Migration to new machine**:
```bash
# Old machine: backup
python cli.py backup --name migration

# New machine: restore
python cli.py restore \
  --postgres-backup db/backups/postgres_backup_migration.sql \
  --neo4j-backup db/backups/neo4j_backup_migration.cypher
```

## Notes

- Backups include embeddings (can be large)
- PostgreSQL ~10MB per 1000 chunks
- Neo4j ~4MB per 1000 chunks
- Backups in `.gitignore` by default
- Does NOT include: Docker images, dependencies, .env, results
