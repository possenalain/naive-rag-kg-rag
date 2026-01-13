#!/usr/bin/env python3
"""Setup script for RAG Benchmarking System - verifies services and initializes database."""

import asyncio
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def check_services():
    """Check PostgreSQL and Neo4j connections."""
    import asyncpg
    from neo4j import AsyncGraphDatabase
    from config.settings import get_settings
    
    settings = get_settings()
    services_ok = True
    
    try:
        conn = await asyncpg.connect(dsn=settings.postgres_url)
        await conn.execute("SELECT 1")
        await conn.close()
        logger.info("✓ PostgreSQL connected")
    except Exception as e:
        logger.error(f"✗ PostgreSQL failed: {e}")
        services_ok = False
    
    try:
        driver = AsyncGraphDatabase.driver(settings.neo4j.uri, auth=(settings.neo4j.user, settings.neo4j.password))
        async with driver.session() as session:
            await session.run("RETURN 1")
        await driver.close()
        logger.info("✓ Neo4j connected")
    except Exception as e:
        logger.error(f"✗ Neo4j failed: {e}")
        services_ok = False
    
    return services_ok


async def initialize_database():
    """Initialize PostgreSQL database schema."""
    import asyncpg
    from config.settings import get_settings
    
    settings = get_settings()
    schema_path = Path("sql/schema.sql")
    
    if not schema_path.exists():
        logger.error("Schema file not found: sql/schema.sql")
        return False
    
    try:
        conn = await asyncpg.connect(dsn=settings.postgres_url)
        await conn.execute(schema_path.read_text())
        
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        table_names = [row['tablename'] for row in tables]
        
        for table in ['documents', 'chunks', 'benchmark_questions', 'evaluations', 'scores']:
            status = "✓" if table in table_names else "✗"
            logger.info(f"{status} Table '{table}'")
        
        await conn.close()
        logger.info("✓ Database initialized")
        return True
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        return False


async def test_llm_connection():
    """Test LLM provider connection."""
    from src.utils.llm import get_llm
    
    try:
        llm = await get_llm()
        response = await llm.generate("Say 'OK' if you can read this.", temperature=0)
        logger.info(f"✓ LLM working: {response[:30]}...")
        return True
    except Exception as e:
        logger.warning(f"⚠ LLM test failed: {e}")
        return False


def check_environment():
    """Check environment configuration."""
    from config.settings import get_settings
    
    env_path = Path(".env")
    if not env_path.exists():
        logger.warning("⚠ .env file not found. Copy .env.example to .env and configure.")
        return False
    
    try:
        settings = get_settings()
        if settings.llm.provider in ['gemini', 'openai'] and not settings.llm.api_key:
            logger.error(f"✗ {settings.llm.provider.upper()}_API_KEY not set")
            return False
        logger.info("✓ Environment configured")
        return True
    except Exception as e:
        logger.error(f"✗ Config error: {e}")
        return False


async def main():
    """Main setup routine - verify environment, services, and initialize database."""
    logger.info("=" * 50)
    logger.info("RAG Benchmarking System - Setup")
    logger.info("=" * 50)
    
    if not check_environment():
        logger.error("\nSetup failed: Configure .env file first")
        sys.exit(1)
    
    if not await check_services():
        logger.error("\nSetup failed: Start services with 'docker-compose up -d'")
        sys.exit(1)
    
    if not await initialize_database():
        logger.error("\nSetup failed: Database initialization error")
        sys.exit(1)
    
    await test_llm_connection()
    
    logger.info("\n" + "=" * 50)
    logger.info("✓ Setup Complete!")
    logger.info("=" * 50)
    logger.info("\nQuick Start:")
    logger.info("  python cli.py ingest ./data/big_tech_docs")
    logger.info("  python cli.py evaluate")
    logger.info("  python cli.py --help")


if __name__ == "__main__":
    asyncio.run(main())
