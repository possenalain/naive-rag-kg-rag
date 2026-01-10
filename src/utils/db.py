"""
Database utilities for PostgreSQL with pgvector support.
Provides async connection pooling, vector operations, and CRUD helpers.
"""

import asyncio
import asyncpg
from typing import List, Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager
import logging
import json
import numpy as np
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseManager:
    """Manages PostgreSQL connection pool and database operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        async with self._lock:
            if self.pool is not None:
                logger.warning("Database pool already initialized")
                return
            
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=settings.postgres_url,
                    min_size=5,
                    max_size=settings.app.db_pool_size,
                    max_inactive_connection_lifetime=300,
                    command_timeout=60
                )
                logger.info("Database connection pool initialized")
                
                # Verify pgvector extension
                async with self.pool.acquire() as conn:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    logger.info("pgvector extension verified")
                    
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise
    
    async def close(self) -> None:
        """Close database connection pool."""
        async with self._lock:
            if self.pool:
                await self.pool.close()
                self.pool = None
                logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for database connections."""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        async with self.connection() as conn:
            async with conn.transaction():
                yield conn
    
    # ===== Document Operations =====
    
    async def insert_document(
        self,
        title: str,
        source_path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Insert a document into the database."""
        query = """
            INSERT INTO documents (title, source_path, content, metadata, ingestion_date)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING document_id
        """
        async with self.connection() as conn:
            document_id = await conn.fetchval(
                query,
                title,
                source_path,
                content,
                json.dumps(metadata or {}),
                datetime.utcnow()
            )
        logger.debug(f"Inserted document: {title} (ID: {document_id})")
        return document_id
    
    async def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        query = "SELECT * FROM documents WHERE document_id = $1"
        async with self.connection() as conn:
            row = await conn.fetchrow(query, document_id)
        return dict(row) if row else None
    
    async def list_documents(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all documents with pagination."""
        query = """
            SELECT document_id, title, source_path, ingestion_date, metadata
            FROM documents
            ORDER BY ingestion_date DESC
            LIMIT $1 OFFSET $2
        """
        async with self.connection() as conn:
            rows = await conn.fetch(query, limit, offset)
        return [dict(row) for row in rows]
    
    async def delete_document(self, document_id: int) -> bool:
        """Delete a document and its chunks."""
        async with self.transaction() as conn:
            # Delete chunks first (cascades to graph nodes)
            await conn.execute(
                "DELETE FROM chunks WHERE document_id = $1",
                document_id
            )
            # Delete document
            result = await conn.execute(
                "DELETE FROM documents WHERE document_id = $1",
                document_id
            )
        success = result.split()[-1] == "1"
        if success:
            logger.info(f"Deleted document ID: {document_id}")
        return success
    
    # ===== Chunk Operations =====
    
    async def insert_chunk(
        self,
        document_id: int,
        chunk_text: str,
        chunk_index: int,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Insert a chunk with its embedding."""
        query = """
            INSERT INTO chunks (document_id, chunk_text, chunk_index, embedding, metadata)
            VALUES ($1, $2, $3, $4::vector, $5)
            RETURNING chunk_id
        """
        # Convert embedding list to postgres vector format string
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
        
        async with self.connection() as conn:
            chunk_id = await conn.fetchval(
                query,
                document_id,
                chunk_text,
                chunk_index,
                embedding_str,
                json.dumps(metadata or {})
            )
        return chunk_id
    
    async def bulk_insert_chunks(
        self,
        chunks: List[Tuple[int, str, int, List[float], Dict[str, Any]]]
    ) -> List[int]:
        """Bulk insert multiple chunks efficiently."""
        query = """
            INSERT INTO chunks (document_id, chunk_text, chunk_index, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING chunk_id
        """
        async with self.connection() as conn:
            chunk_ids = await conn.fetch(query, *zip(*chunks))
        logger.info(f"Bulk inserted {len(chunks)} chunks")
        return [row['chunk_id'] for row in chunk_ids]
    
    async def get_chunk(self, chunk_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a chunk by ID."""
        query = "SELECT * FROM chunks WHERE chunk_id = $1"
        async with self.connection() as conn:
            row = await conn.fetchrow(query, chunk_id)
        return dict(row) if row else None
    
    async def get_document_chunks(
        self,
        document_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        query = """
            SELECT chunk_id, chunk_text, chunk_index, metadata
            FROM chunks
            WHERE document_id = $1
            ORDER BY chunk_index
            LIMIT $2
        """
        async with self.connection() as conn:
            rows = await conn.fetch(query, document_id, limit)
        return [dict(row) for row in rows]
    
    # ===== Vector Search Operations =====
    
    async def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform cosine similarity search on chunk embeddings.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            document_ids: Optional filter by document IDs
        
        Returns:
            List of chunks with similarity scores
        """
        # Convert embedding list to PostgreSQL vector format string
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
        
        # Use a subquery to avoid PostgreSQL recalculating the distance in WHERE clause
        # This significantly improves performance
        query = """
            WITH ranked_chunks AS (
                SELECT 
                    c.chunk_id,
                    c.document_id,
                    c.chunk_text,
                    c.chunk_index,
                    c.metadata,
                    1 - (c.embedding <=> $1::vector) as similarity_score
                FROM chunks c
        """
        
        params = [embedding_str]
        
        # Optional document filter in the CTE
        if document_ids:
            query += " WHERE c.document_id = ANY($2)"
            params.append(document_ids)
        
        # Complete the CTE and join with documents
        query += """
            )
            SELECT 
                rc.chunk_id,
                rc.document_id,
                rc.chunk_text,
                rc.chunk_index,
                rc.metadata,
                d.title as document_title,
                d.source_path,
                rc.similarity_score
            FROM ranked_chunks rc
            JOIN documents d ON rc.document_id = d.document_id
            WHERE rc.similarity_score >= $""" + str(len(params) + 1) + """
            ORDER BY rc.similarity_score DESC
            LIMIT $""" + str(len(params) + 2)
        
        params.extend([similarity_threshold, top_k])
        
        # Debug logging
        logger.info(f"Vector search with similarity_threshold={similarity_threshold}, top_k={top_k}")
        
        async with self.connection() as conn:
            rows = await conn.fetch(query, *params)
        
        logger.info(f"Vector search returned {len(rows)} rows")
        results = [dict(row) for row in rows]
        return results
    
    async def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 5,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and text search.
        
        Uses Reciprocal Rank Fusion (RRF) to combine rankings.
        """
        # Vector search
        vector_results = await self.vector_search(query_embedding, top_k * 2)
        
        # Text search using tsvector
        text_query = """
            SELECT 
                c.chunk_id,
                c.document_id,
                c.chunk_text,
                c.chunk_index,
                c.metadata,
                d.title as document_title,
                d.source_path,
                ts_rank(to_tsvector('english', c.chunk_text), plainto_tsquery('english', $1)) as text_score
            FROM chunks c
            JOIN documents d ON c.document_id = d.document_id
            WHERE to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', $1)
            ORDER BY text_score DESC
            LIMIT $2
        """
        async with self.connection() as conn:
            text_rows = await conn.fetch(text_query, query_text, top_k * 2)
        text_results = [dict(row) for row in text_rows]
        
        # RRF fusion
        rrf_k = 60  # Standard RRF constant
        chunk_scores = {}
        
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result['chunk_id']
            chunk_scores[chunk_id] = {
                'chunk': result,
                'rrf_score': vector_weight / (rrf_k + rank)
            }
        
        for rank, result in enumerate(text_results, start=1):
            chunk_id = result['chunk_id']
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]['rrf_score'] += (1 - vector_weight) / (rrf_k + rank)
            else:
                chunk_scores[chunk_id] = {
                    'chunk': result,
                    'rrf_score': (1 - vector_weight) / (rrf_k + rank)
                }
        
        # Sort by RRF score and return top-k
        sorted_results = sorted(
            chunk_scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )[:top_k]
        
        final_results = []
        for item in sorted_results:
            chunk = item['chunk']
            chunk['rrf_score'] = item['rrf_score']
            final_results.append(chunk)
        
        logger.debug(f"Hybrid search returned {len(final_results)} results")
        return final_results
    
    # ===== Benchmark Operations =====
    
    async def insert_benchmark_question(
        self,
        dataset_name: str,
        question_id: str,
        question_text: str,
        ground_truth: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Insert a benchmark question."""
        query = """
            INSERT INTO benchmark_questions 
            (dataset_name, question_id, question_text, ground_truth, context, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (dataset_name, question_id) DO UPDATE
            SET question_text = EXCLUDED.question_text,
                ground_truth = EXCLUDED.ground_truth,
                context = EXCLUDED.context,
                metadata = EXCLUDED.metadata
            RETURNING id
        """
        async with self.connection() as conn:
            row_id = await conn.fetchval(
                query,
                dataset_name,
                question_id,
                question_text,
                ground_truth,
                context,
                metadata or {}
            )
        return row_id
    
    async def get_benchmark_questions(
        self,
        dataset_name: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get benchmark questions for a dataset."""
        query = """
            SELECT * FROM benchmark_questions
            WHERE dataset_name = $1
            ORDER BY question_id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        async with self.connection() as conn:
            rows = await conn.fetch(query, dataset_name)
        return [dict(row) for row in rows]
    
    # ===== Evaluation Operations =====
    
    async def insert_evaluation(
        self,
        rag_variant: str,
        question_id: int,
        generated_answer: str,
        retrieved_chunks: List[int],
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Insert an evaluation result."""
        query = """
            INSERT INTO evaluations 
            (rag_variant, question_id, generated_answer, retrieved_chunks, latency_ms, metadata, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING evaluation_id
        """
        async with self.connection() as conn:
            eval_id = await conn.fetchval(
                query,
                rag_variant,
                question_id,
                generated_answer,
                retrieved_chunks,
                latency_ms,
                metadata or {},
                datetime.utcnow()
            )
        return eval_id
    
    async def insert_scores(
        self,
        evaluation_id: int,
        correctness: float,
        completeness: float,
        relevance: float,
        faithfulness: float,
        clarity: float,
        explanation: Optional[Dict[str, str]] = None
    ) -> int:
        """Insert evaluation scores."""
        query = """
            INSERT INTO scores 
            (evaluation_id, correctness, completeness, relevance, faithfulness, clarity, explanation)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING score_id
        """
        async with self.connection() as conn:
            score_id = await conn.fetchval(
                query,
                evaluation_id,
                correctness,
                completeness,
                relevance,
                faithfulness,
                clarity,
                explanation or {}
            )
        return score_id
    
    async def get_evaluation_results(
        self,
        rag_variant: Optional[str] = None,
        dataset_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get evaluation results with scores."""
        query = """
            SELECT 
                e.*,
                s.correctness,
                s.completeness,
                s.relevance,
                s.faithfulness,
                s.clarity,
                s.explanation,
                bq.question_text,
                bq.ground_truth,
                bq.dataset_name
            FROM evaluations e
            LEFT JOIN scores s ON e.evaluation_id = s.evaluation_id
            JOIN benchmark_questions bq ON e.question_id = bq.id
        """
        
        conditions = []
        params = []
        
        if rag_variant:
            conditions.append(f"e.rag_variant = ${len(params) + 1}")
            params.append(rag_variant)
        
        if dataset_name:
            conditions.append(f"bq.dataset_name = ${len(params) + 1}")
            params.append(dataset_name)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY e.timestamp DESC"
        
        async with self.connection() as conn:
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> DatabaseManager:
    """Get database manager instance."""
    if not db_manager.pool:
        await db_manager.initialize()
    return db_manager


if __name__ == "__main__":
    import sys
    import os
    
    async def init_database():
        """Initialize database schema from SQL file."""
        try:
            # Initialize connection
            await db_manager.initialize()
            logger.info("Database connection initialized")
            
            # Read schema file
            schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "schema.sql")
            schema_path = os.path.normpath(schema_path)
            
            if not os.path.exists(schema_path):
                logger.error(f"Schema file not found: {schema_path}")
                return False
            
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            logger.info(f"Loaded schema from {schema_path}")
            
            # Execute schema
            async with db_manager.connection() as conn:
                await conn.execute(schema_sql)
            
            logger.info("Database schema initialized successfully")
            
            await db_manager.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            await db_manager.close()
            return False
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        logging.basicConfig(level=logging.INFO)
        success = asyncio.run(init_database())
        sys.exit(0 if success else 1)
    else:
        print("Usage: python -m src.utils.db init")
        sys.exit(1)
