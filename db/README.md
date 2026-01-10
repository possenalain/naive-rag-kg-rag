# Database Backups

This directory stores backups of PostgreSQL and Neo4j databases.

## Directory Structure

```
db/
└── backups/
    ├── postgres_backup_20260110_153045.sql
    ├── postgres_backup_20260110_153045_metadata.json
    ├── neo4j_backup_20260110_153045.cypher
    └── neo4j_backup_20260110_153045_metadata.json
```

## Usage

### Create Backup

```bash
# Backup both databases
python cli.py backup

# Backup with custom name
python cli.py backup --name my_backup

# Backup PostgreSQL only
python cli.py backup --postgres-only

# Backup Neo4j only
python cli.py backup --neo4j-only
```

### List Backups

```bash
python cli.py restore --list-backups
```

### Restore from Backup

```bash
# Restore both databases
python cli.py restore \
  --postgres-backup db/backups/postgres_backup_20260110.sql \
  --neo4j-backup db/backups/neo4j_backup_20260110.cypher

# Restore PostgreSQL only
python cli.py restore --postgres-backup db/backups/postgres_backup_20260110.sql

# Restore Neo4j only
python cli.py restore --neo4j-backup db/backups/neo4j_backup_20260110.cypher
```

## Backup Contents

### PostgreSQL Backup (.sql)
- Complete database dump with schema
- All documents, chunks, embeddings
- Evaluation history
- Includes DROP/CREATE statements for clean restore

### Neo4j Backup (.cypher)
- All nodes (entities, chunks, episodes)
- Node properties and labels
- Relationships between nodes
- Cypher statements for recreation

### Metadata (.json)
- Backup timestamp
- Database statistics (document count, chunk count, etc.)
- Database version info

## Best Practices

1. **Backup before major changes**
   ```bash
   python cli.py backup --name before_new_ingestion
   ```

2. **Regular backups**
   - Daily: `python cli.py backup`
   - Keep last 7 days

3. **Backup before reset**
   ```bash
   python cli.py backup
   python cli.py reset
   ```

4. **Test restores**
   - Periodically verify backups can be restored

5. **Version control**
   - Backups are in `.gitignore` by default
   - For important datasets, store elsewhere

## Automation

### Daily Backup Script (PowerShell)

```powershell
# backup_daily.ps1
cd "X:\path\to\naive-rag-kg-rag"
$date = Get-Date -Format "yyyyMMdd"
uv run python cli.py backup --name "daily_$date"

# Delete backups older than 7 days
Get-ChildItem db\backups -Filter "*_metadata.json" | 
  Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-7) } |
  ForEach-Object { 
    Remove-Item $_.FullName
    Remove-Item $_.FullName.Replace("_metadata.json", ".sql") -ErrorAction SilentlyContinue
    Remove-Item $_.FullName.Replace("_metadata.json", ".cypher") -ErrorAction SilentlyContinue
  }
```

### Scheduled Task (Windows)

```powershell
# Run daily at 2 AM
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\path\to\backup_daily.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "RAG_Daily_Backup" -Action $action -Trigger $trigger
```

## Recovery Scenarios

### Scenario 1: Accidental Data Deletion

```bash
# Restore latest backup
python cli.py restore --list-backups  # Find latest
python cli.py restore --postgres-backup db/backups/postgres_backup_LATEST.sql --neo4j-backup db/backups/neo4j_backup_LATEST.cypher
```

### Scenario 2: Testing New Features

```bash
# Backup current state
python cli.py backup --name before_experiment

# Test changes...

# Restore if needed
python cli.py restore --postgres-backup db/backups/postgres_backup_before_experiment.sql --neo4j-backup db/backups/neo4j_backup_before_experiment.cypher
```

### Scenario 3: Moving to New Machine

```bash
# On old machine
python cli.py backup --name migration

# Copy db/backups/ to new machine

# On new machine (after docker-compose up)
python cli.py restore --postgres-backup db/backups/postgres_backup_migration.sql --neo4j-backup db/backups/neo4j_backup_migration.cypher
```

## Troubleshooting

### Backup fails: "docker: command not found"
- Install Docker Desktop
- Ensure Docker containers are running: `docker ps`

### Restore fails: "database does not exist"
- Ensure containers are running
- Check connection settings in `.env`

### Large backup files
- PostgreSQL: Compress with `gzip postgres_backup.sql`
- Neo4j: For large graphs, consider Neo4j admin tools

### Backup takes too long
- Use `--postgres-only` or `--neo4j-only` for partial backups
- Schedule backups during off-hours

## Notes

- **PostgreSQL backups** include embeddings (large files)
- **Neo4j backups** include full graph structure
- Backups do NOT include:
  - Docker images
  - Python dependencies
  - Configuration files (.env)
  - Evaluation result files

## Backup Size Estimates

| Documents | Chunks | PostgreSQL | Neo4j |
|-----------|--------|------------|-------|
| 10        | 500    | ~5 MB      | ~2 MB |
| 50        | 2,500  | ~25 MB     | ~10 MB |
| 100       | 5,000  | ~50 MB     | ~20 MB |
| 500       | 25,000 | ~250 MB    | ~100 MB |

*Sizes vary based on document content and embedding dimensions*
