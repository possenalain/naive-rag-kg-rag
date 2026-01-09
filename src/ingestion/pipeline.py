"""
Main ingestion pipeline orchestrating document loading, chunking, 
embedding, and knowledge graph construction.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from tqdm.asyncio import tqdm
from datetime import datetime

from src.ingestion.document_loader import DocumentLoader, Document
from src.ingestion.semantic_chunker import SemanticChunker, Chunk
from src.ingestion.embedding_service import EmbeddingService
from src.utils.db import get_db
from src.utils.graph import get_graph
from src.utils.llm import get_llm
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class IngestionPipeline:
    """
    End-to-end ingestion pipeline:
    1. Load documents from source
    2. Chunk documents semantically
    3. Generate embeddings
    4. Store in PostgreSQL
    5. Build knowledge graph in Neo4j
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        enable_kg: bool = True,
        enable_cache: bool = True
    ):
        """
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks
            enable_kg: Whether to build knowledge graph
            enable_cache: Whether to cache embeddings
        """
        self.chunk_size = chunk_size or settings.ingestion.chunk_size
        self.chunk_overlap = chunk_overlap or settings.ingestion.chunk_overlap
        self.enable_kg = enable_kg
        
        # Initialize components
        self.loader = DocumentLoader()
        self.chunker = SemanticChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            max_chunk_size=settings.ingestion.max_chunk_size
        )
        self.embedder = EmbeddingService(enable_cache=enable_cache)
        
        self.db = None
        self.graph = None
        self.llm = None
    
    async def initialize(self):
        """Initialize database connections and services."""
        logger.info("Initializing ingestion pipeline...")
        
        self.db = await get_db()
        await self.embedder.initialize()
        
        if self.enable_kg:
            self.graph = await get_graph()
            self.llm = await get_llm()
        
        logger.info("Ingestion pipeline initialized")
    
    async def ingest_directory(
        self,
        directory: Path,
        recursive: bool = True,
        file_pattern: str = "*.*"
    ) -> Dict[str, Any]:
        """
        Ingest all documents from a directory.
        
        Returns:
            Statistics about the ingestion process
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting ingestion from: {directory}")
        
        # Step 1: Load documents
        logger.info("Step 1/5: Loading documents...")
        documents = await self.loader.load_directory(
            directory, recursive=recursive, file_pattern=file_pattern
        )
        
        if not documents:
            logger.warning("No documents loaded")
            return {'status': 'failed', 'reason': 'No documents found'}
        
        doc_stats = self.loader.get_document_stats(documents)
        logger.info(f"Loaded {doc_stats['total_documents']} documents, "
                   f"{doc_stats['total_words']:,} words")
        
        # Step 2: Chunk documents
        logger.info("Step 2/5: Chunking documents...")
        doc_chunks = self.chunker.chunk_documents(documents)
        all_chunks = [chunk for _, chunks in doc_chunks for chunk in chunks]
        chunk_stats = self.chunker.get_chunk_stats(all_chunks)
        logger.info(f"Created {chunk_stats['total_chunks']} chunks, "
                   f"avg {chunk_stats['avg_tokens']} tokens/chunk")
        
        # Step 3: Generate embeddings
        logger.info("Step 3/5: Generating embeddings...")
        embeddings = await self.embedder.embed_batch([c.text for c in all_chunks])
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Step 4: Store in PostgreSQL
        logger.info("Step 4/5: Storing in PostgreSQL...")
        stored_chunks = await self._store_in_postgres(documents, doc_chunks, embeddings)
        logger.info(f"Stored {len(stored_chunks)} chunks in database")
        
        # Step 5: Build knowledge graph (optional)
        kg_stats = {}
        if self.enable_kg:
            logger.info("Step 5/5: Building knowledge graph...")
            kg_stats = await self._build_knowledge_graph(documents, stored_chunks)
            logger.info(f"Knowledge graph built: {kg_stats['entities_created']} entities")
        else:
            logger.info("Step 5/5: Skipping knowledge graph")
        
        # Compute stats
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'status': 'success',
            'duration_seconds': duration,
            'documents_processed': len(documents),
            'chunks_created': len(all_chunks),
            'embeddings_generated': len(embeddings),
            'knowledge_graph': kg_stats,
            'doc_stats': doc_stats,
            'chunk_stats': chunk_stats
        }
    
    async def ingest_single_document(
        self,
        file_path: Path
    ) -> Dict[str, Any]:
        """Ingest a single document."""
        logger.info(f"Ingesting single document: {file_path}")
        
        # Load document
        document = await self.loader.load_file(file_path)
        if not document:
            return {'status': 'failed', 'reason': 'Failed to load document'}
        
        # Chunk
        chunks = self.chunker.chunk_text(document.content, document.metadata)
        if not chunks:
            return {'status': 'failed', 'reason': 'Failed to chunk document'}
        
        # Embed
        embeddings = await self.embedder.embed_batch([c.text for c in chunks])
        
        # Store
        stored_chunks = await self._store_in_postgres([document], [(document, chunks)], embeddings)
        
        # Build KG
        kg_stats = {}
        if self.enable_kg:
            kg_stats = await self._build_knowledge_graph([document], stored_chunks)
        
        return {
            'status': 'success',
            'document_title': document.title,
            'chunks_created': len(chunks),
            'knowledge_graph': kg_stats
        }
    
    async def _store_in_postgres(
        self,
        documents: List[Document],
        doc_chunks: List[tuple],  # List of (document, chunks) tuples
        embeddings: List[List[float]]
    ) -> List[Dict[str, Any]]:
        """Store documents and chunks in PostgreSQL."""
        stored_chunks = []
        embedding_idx = 0
        
        # Iterate through doc_chunks tuples
        for document, chunks in doc_chunks:
            try:
                # Insert document
                doc_id = await self.db.insert_document(
                    title=document.title,
                    source_path=document.source_path,
                    content=document.content,
                    metadata=document.metadata
                )
                
                # Insert chunks for this document
                for chunk in chunks:
                    embedding = embeddings[embedding_idx]
                    embedding_idx += 1
                    
                    chunk_id = await self.db.insert_chunk(
                        document_id=doc_id,
                        chunk_text=chunk.text,
                        chunk_index=chunk.chunk_index,
                        embedding=embedding,
                        metadata=chunk.metadata
                    )
                    
                    stored_chunks.append({
                        'chunk_id': chunk_id,
                        'document_id': doc_id,
                        'chunk_text': chunk.text,
                        'chunk_index': chunk.chunk_index,
                        'embedding': embedding
                    })
                
                logger.debug(f"Stored document '{document.title}' with {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error storing document '{document.title}': {e}")
                continue
        
        return stored_chunks
    
    async def _build_knowledge_graph(
        self,
        documents: List[Document],
        stored_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build knowledge graph using Graphiti."""
        entities_created = 0
        chunk_nodes_created = 0
        
        try:
            # Step 1: Create chunk nodes in Neo4j
            logger.info("Creating chunk nodes in Neo4j...")
            chunk_data = [
                {
                    'chunk_id': c['chunk_id'],
                    'chunk_text': c['chunk_text'],
                    'document_id': c['document_id'],
                    'chunk_index': c['chunk_index']
                }
                for c in stored_chunks
            ]
            
            node_ids = await self.graph.bulk_create_chunk_nodes(chunk_data)
            chunk_nodes_created = len(node_ids)
            logger.info(f"Created {chunk_nodes_created} chunk nodes")
            
            # Step 2: Extract entities using Graphiti
            logger.info("Extracting entities with Graphiti...")
            
            # Group chunks by document for better context
            doc_chunk_map = {}
            for chunk in stored_chunks:
                doc_id = chunk['document_id']
                if doc_id not in doc_chunk_map:
                    doc_chunk_map[doc_id] = []
                doc_chunk_map[doc_id].append(chunk)
            
            # Process each document's chunks
            for doc_id, chunks in doc_chunk_map.items():
                # Find corresponding document
                doc = next((d for i, d in enumerate(documents) if i == 0), None)
                if not doc:
                    continue
                
                # Add episodes to Graphiti (max 10 per doc to avoid overwhelming)
                for i, chunk in enumerate(chunks[:10]):

                        try:
                            episode = await self.graph.add_episode(
                                name=f"{doc.title} - Chunk {chunk['chunk_index']}",
                                content=chunk['chunk_text'],
                                source_description=f"Chunk {chunk['chunk_index']} from document '{doc.title}' (source: {doc.source_path}, chunk_id: {chunk['chunk_id']}, document_id: {doc_id})"
                            )
                            entities_created += 1
                            
                            # Link chunk to entities (simplified - Graphiti handles internally)
                            logger.debug(f"Added episode for chunk {chunk['chunk_id']}")
                        except Exception as e:
                            error_msg = str(e).lower()
                            if "rate limit" in error_msg:
                                logger.warning(f"Rate limit hit when adding episode for chunk {chunk['chunk_id']}")
                                logger.error(f"{e}")
                                break
                            else:
                                logger.warning(f"Error adding episode for chunk {chunk['chunk_id']}: {e}")
                                continue 
            
            logger.info(f"Entity extraction complete: {entities_created} episodes added")
            
        except Exception as e:
            logger.error(f"Error building knowledge graph: {e}")
        
        return {
            'entities_created': entities_created,
            'chunk_nodes_created': chunk_nodes_created
        }


# Example usage
if __name__ == "__main__":
    async def test_pipeline():
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create pipeline
        pipeline = IngestionPipeline(enable_kg=True)
        await pipeline.initialize()
        
        # Ingest documents
        docs_dir = Path("./big_tech_docs")
        if docs_dir.exists():
            stats = await pipeline.ingest_directory(docs_dir)
            print(f"\nIngestion complete!")
            print(f"Duration: {stats['duration_seconds']:.2f}s")
            print(f"Documents: {stats['documents_processed']}")
            print(f"Chunks: {stats['chunks_created']}")
            print(f"KG Entities: {stats['knowledge_graph'].get('entities_created', 0)}")
        else:
            print(f"Directory not found: {docs_dir}")
    
    asyncio.run(test_pipeline())
