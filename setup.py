#!/usr/bin/env python3
"""
Setup and startup script for RAG Benchmarking System.
Initializes environment and verifies all dependencies.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_services():
    """Check if required services are running."""
    import asyncpg
    from neo4j import AsyncGraphDatabase
    from config.settings import get_settings
    
    settings = get_settings()
    services_ok = True
    
    # Check PostgreSQL
    logger.info("Checking PostgreSQL connection...")
    try:
        conn = await asyncpg.connect(dsn=settings.postgres_url)
        await conn.execute("SELECT 1")
        await conn.close()
        logger.info("✓ PostgreSQL is running")
    except Exception as e:
        logger.error(f"✗ PostgreSQL connection failed: {e}")
        services_ok = False
    
    # Check Neo4j
    logger.info("Checking Neo4j connection...")
    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.user, settings.neo4j.password)
        )
        async with driver.session() as session:
            await session.run("RETURN 1")
        await driver.close()
        logger.info("✓ Neo4j is running")
    except Exception as e:
        logger.error(f"✗ Neo4j connection failed: {e}")
        services_ok = False
    
    return services_ok


async def initialize_database():
    """Initialize database schema."""
    import asyncpg
    from config.settings import get_settings
    
    settings = get_settings()
    
    logger.info("Initializing database schema...")
    
    # Read schema file
    schema_path = Path("sql/schema.sql")
    if not schema_path.exists():
        logger.error("Schema file not found: sql/schema.sql")
        return False
    
    schema_sql = schema_path.read_text()
    
    try:
        conn = await asyncpg.connect(dsn=settings.postgres_url)
        
        # Execute schema
        await conn.execute(schema_sql)
        
        # Verify tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        table_names = [row['tablename'] for row in tables]
        
        required_tables = ['documents', 'chunks', 'benchmark_questions', 'evaluations', 'scores']
        for table in required_tables:
            if table in table_names:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.warning(f"✗ Table '{table}' not found")
        
        await conn.close()
        logger.info("✓ Database schema initialized")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        return False


async def test_llm_connection():
    """Test LLM provider connection."""
    from src.utils.llm import get_llm
    from config.settings import get_settings
    
    settings = get_settings()
    
    logger.info(f"Testing LLM connection ({settings.llm.provider})...")
    
    try:
        llm = await get_llm()
        response = await llm.generate("Say 'OK' if you can read this.", temperature=0)
        
        if response:
            logger.info(f"✓ LLM is working: {response[:50]}")
            return True
        else:
            logger.error("✗ LLM returned empty response")
            return False
            
    except Exception as e:
        logger.error(f"✗ LLM connection failed: {e}")
        return False


def check_environment():
    """Check environment variables."""
    from config.settings import get_settings
    import os
    
    logger.info("Checking environment configuration...")
    
    required_vars = []
    optional_vars = ['POSTGRES_PASSWORD', 'NEO4J_PASSWORD']
    
    # Check if .env exists
    env_path = Path(".env")
    if not env_path.exists():
        logger.warning("✗ .env file not found. Copy .env.example to .env and configure.")
        return False
    
    settings = get_settings()
    
    # Check LLM API key if using cloud provider
    if settings.llm.provider in ['gemini', 'openai']:
        if not settings.llm.api_key:
            logger.error(f"✗ {settings.llm.provider.upper()}_API_KEY not set")
            return False
        else:
            logger.info(f"✓ {settings.llm.provider.upper()}_API_KEY is set")
    
    logger.info("✓ Environment configuration OK")
    return True


async def main():
    """Main setup routine."""
    logger.info("=" * 60)
    logger.info("RAG Benchmarking System - Setup & Verification")
    logger.info("=" * 60)
    
    # Step 1: Check environment
    if not check_environment():
        logger.error("\nSetup failed: Environment configuration issues")
        logger.info("\nPlease:")
        logger.info("1. Copy .env.example to .env")
        logger.info("2. Configure API keys and passwords")
        logger.info("3. Run this script again")
        sys.exit(1)
    
    # Step 2: Check services
    if not await check_services():
        logger.error("\nSetup failed: Required services not running")
        logger.info("\nPlease start services with:")
        logger.info("  docker-compose up -d")
        logger.info("\nThen run this script again")
        sys.exit(1)
    
    # Step 3: Initialize database
    if not await initialize_database():
        logger.error("\nSetup failed: Database initialization issues")
        sys.exit(1)
    
    # Step 4: Test LLM
    if not await test_llm_connection():
        logger.warning("\nWarning: LLM connection test failed")
        logger.info("The system may still work if you're using local models")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Setup Complete! System is ready to use.")
    logger.info("=" * 60)
    logger.info("\nQuick Start:")
    logger.info("  1. Ingest documents:  python cli.py ingest ./big_tech_docs")
    logger.info("  2. Run evaluation:    python cli.py evaluate")
    logger.info("  3. Query system:      python cli.py query 'Your question?'")
    logger.info("\nFor more commands:    python cli.py --help")


if __name__ == "__main__":
    asyncio.run(main())
