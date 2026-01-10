"""Database backup and restore utilities."""

import asyncio
import subprocess
import json
from pathlib import Path
from datetime import datetime
from neo4j.time import DateTime as Neo4jDateTime
import click
from config.settings import get_settings
from src.utils.db import get_db
from src.utils.graph import get_graph

settings = get_settings()


def serialize_neo4j_value(value):
    """Convert Neo4j types to JSON-serializable types."""
    if isinstance(value, Neo4jDateTime):
        return value.isoformat() if hasattr(value, 'isoformat') else str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: serialize_neo4j_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [serialize_neo4j_value(v) for v in value]
    return value


async def backup_postgres(backup_dir: Path, backup_name: str = None) -> Path:
    """Backup PostgreSQL database using pg_dump.
    
    Args:
        backup_dir: Directory to store backup
        backup_name: Optional custom backup name
        
    Returns:
        Path to backup file
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if not backup_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"postgres_backup_{timestamp}"
    
    backup_file = backup_dir / f"{backup_name}.sql"
    
    # Use pg_dump to create backup
    env = {
        "PGPASSWORD": settings.database.password
    }
    
    cmd = [
        "docker", "exec", "-i", "rag_postgres",
        "pg_dump",
        "-U", settings.database.user,
        "-d", settings.database.db,
        "--clean",  # Include DROP statements
        "--if-exists",  # Add IF EXISTS to DROP statements
        "--no-owner",  # Don't set ownership
        "--no-acl",  # Don't set privileges
    ]
    
    click.echo(f"Backing up PostgreSQL to: {backup_file}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        backup_file.write_text(result.stdout)
        
        # Also save metadata
        db = await get_db()
        async with db.connection() as conn:
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        
        metadata = {
            "backup_time": datetime.now().isoformat(),
            "backup_name": backup_name,
            "database": settings.database.db,
            "document_count": doc_count,
            "chunk_count": chunk_count,
        }
        
        metadata_file = backup_dir / f"{backup_name}_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        click.echo(f"✓ PostgreSQL backup complete")
        click.echo(f"  Documents: {doc_count}")
        click.echo(f"  Chunks: {chunk_count}")
        click.echo(f"  Size: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")
        
        return backup_file
        
    except subprocess.CalledProcessError as e:
        click.echo(f"✗ Backup failed: {e.stderr}", err=True)
        raise


async def restore_postgres(backup_file: Path) -> None:
    """Restore PostgreSQL database from backup.
    
    Args:
        backup_file: Path to backup SQL file
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
    
    click.echo(f"Restoring PostgreSQL from: {backup_file}")
    
    # Read backup file
    sql_content = backup_file.read_text()
    
    # Use psql to restore
    cmd = [
        "docker", "exec", "-i", "rag_postgres",
        "psql",
        "-U", settings.database.user,
        "-d", settings.database.db,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=sql_content,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Verify restoration
        db = await get_db()
        async with db.connection() as conn:
            doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
            chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        
        click.echo(f"✓ PostgreSQL restore complete")
        click.echo(f"  Documents: {doc_count}")
        click.echo(f"  Chunks: {chunk_count}")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"✗ Restore failed: {e.stderr}", err=True)
        raise


async def backup_neo4j(backup_dir: Path, backup_name: str = None) -> Path:
    """Backup Neo4j database using Cypher export.
    
    Args:
        backup_dir: Directory to store backup
        backup_name: Optional custom backup name
        
    Returns:
        Path to backup file
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if not backup_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"neo4j_backup_{timestamp}"
    
    backup_file = backup_dir / f"{backup_name}.cypher"
    
    click.echo(f"Backing up Neo4j to: {backup_file}")
    
    graph = await get_graph()
    
    # Get all nodes and relationships
    export_queries = []
    
    # Export nodes
    click.echo("  Exporting nodes...")
    node_query = """
    MATCH (n)
    RETURN labels(n) as labels, properties(n) as props
    """
    nodes = await graph.driver.execute_query(node_query)
    
    for record in nodes.records:
        labels = ":".join(record["labels"])
        props = record["props"]
        # Serialize Neo4j datetime types
        props = serialize_neo4j_value(props)
        props_str = ", ".join([f"{k}: {json.dumps(v)}" for k, v in props.items()])
        export_queries.append(f"CREATE (:{labels} {{{props_str}}});")
    
    # Export relationships
    click.echo("  Exporting relationships...")
    rel_query = """
    MATCH (a)-[r]->(b)
    RETURN 
        id(a) as source_id,
        labels(a) as source_labels,
        properties(a) as source_props,
        type(r) as rel_type,
        properties(r) as rel_props,
        id(b) as target_id,
        labels(b) as target_labels,
        properties(b) as target_props
    """
    rels = await graph.driver.execute_query(rel_query)
    
    # Write header
    cypher_content = [
        "// Neo4j Database Backup",
        f"// Created: {datetime.now().isoformat()}",
        f"// Database: {settings.neo4j.uri}",
        "",
        "// Clear existing data",
        "MATCH (n) DETACH DELETE n;",
        "",
        "// Create nodes",
    ]
    
    cypher_content.extend(export_queries)
    cypher_content.append("")
    cypher_content.append("// Create relationships")
    
    # Note: Full relationship export with node matching would be complex
    # For now, export node data. For production, consider Neo4j's native backup tools
    
    backup_file.write_text("\n".join(cypher_content))
    
    # Save metadata
    stats = await graph.get_graph_stats()
    metadata = {
        "backup_time": datetime.now().isoformat(),
        "backup_name": backup_name,
        "node_count": len(nodes.records),
        "chunk_count": stats.get('chunk_count', 0),
        "entity_count": stats.get('entity_count', 0),
        "relation_count": stats.get('entity_relations', 0),
    }
    
    metadata_file = backup_dir / f"{backup_name}_metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    
    click.echo(f"✓ Neo4j backup complete")
    click.echo(f"  Nodes: {len(nodes.records)}")
    click.echo(f"  Entities: {stats.get('entity_count', 0)}")
    click.echo(f"  Size: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    return backup_file


async def backup_neo4j_admin(backup_dir: Path, backup_name: str = None) -> Path:
    """Backup Neo4j using admin dump (recommended for large databases).
    
    Args:
        backup_dir: Directory to store backup
        backup_name: Optional custom backup name
        
    Returns:
        Path to backup directory
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if not backup_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"neo4j_admin_backup_{timestamp}"
    
    backup_path = backup_dir / backup_name
    
    click.echo(f"Backing up Neo4j (admin dump) to: {backup_path}")
    
    # Stop Neo4j, backup, restart (for community edition)
    # Note: This requires proper setup. Alternative: use APOC export
    click.echo("⚠ Admin dump requires Neo4j to be stopped")
    click.echo("Using Cypher export instead (see backup_neo4j)")
    
    return await backup_neo4j(backup_dir, backup_name)


async def restore_neo4j(backup_file: Path) -> None:
    """Restore Neo4j database from backup.
    
    Args:
        backup_file: Path to backup Cypher file
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
    
    click.echo(f"Restoring Neo4j from: {backup_file}")
    
    graph = await get_graph()
    
    # Clear existing data
    click.echo("  Clearing existing graph...")
    await graph.clear_graph()
    
    # Read and execute backup file
    click.echo("  Restoring nodes and relationships...")
    cypher_content = backup_file.read_text()
    
    # Split into statements and execute
    statements = [s.strip() for s in cypher_content.split(';') if s.strip() and not s.strip().startswith('//')]
    
    for i, statement in enumerate(statements):
        if i % 100 == 0:
            click.echo(f"    Processed {i}/{len(statements)} statements...")
        
        try:
            await graph.driver.execute_query(statement)
        except Exception as e:
            click.echo(f"    Warning: Failed to execute statement {i}: {e}")
    
    # Verify restoration
    stats = await graph.get_graph_stats()
    
    click.echo(f"✓ Neo4j restore complete")
    click.echo(f"  Chunks: {stats.get('chunk_count', 0)}")
    click.echo(f"  Entities: {stats.get('entity_count', 0)}")
    click.echo(f"  Relations: {stats.get('entity_relations', 0)}")


async def list_backups(backup_dir: Path) -> list:
    """List available backups.
    
    Args:
        backup_dir: Directory containing backups
        
    Returns:
        List of backup metadata
    """
    if not backup_dir.exists():
        return []
    
    backups = []
    
    # Find all metadata files
    for metadata_file in backup_dir.glob("*_metadata.json"):
        try:
            metadata = json.loads(metadata_file.read_text())
            backups.append(metadata)
        except Exception as e:
            click.echo(f"Warning: Could not read {metadata_file}: {e}")
    
    # Sort by backup time
    backups.sort(key=lambda x: x.get('backup_time', ''), reverse=True)
    
    return backups
