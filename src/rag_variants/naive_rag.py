"""
Naive RAG: Traditional vector-based retrieval.
Uses cosine similarity search on chunk embeddings.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.utils.db import get_db
from src.utils.llm import get_llm
from src.ingestion.embedding_service import EmbeddingService
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NaiveRAG:
    """
    Naive RAG implementation using vector similarity search.
    
    Pipeline:
    1. Embed user query
    2. Retrieve top-k similar chunks via cosine similarity
    3. Construct prompt with retrieved context
    4. Generate answer using LLM
    """
    
    def __init__(self, top_k: Optional[int] = None):
        """
        Args:
            top_k: Number of chunks to retrieve
        """
        self.top_k = top_k or settings.rag.top_k
        self.db = None
        self.llm = None
        self.embedder = EmbeddingService()
    
    async def initialize(self):
        """Initialize database and LLM connections."""
        if self.db is None:
            self.db = await get_db()
            self.llm = await get_llm()
            await self.embedder.initialize()
            logger.info("NaiveRAG initialized")
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using vector similarity.
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score (uses config default if None)
        
        Returns:
            List of retrieved chunks with metadata
        """
        if not self.db:
            await self.initialize()
        
        k = top_k or self.top_k
        threshold = similarity_threshold if similarity_threshold is not None else settings.rag.vector_similarity_threshold
        
        # Step 1: Embed query
        logger.debug(f"Embedding query: {query}")
        query_embedding = await self.embedder.embed_text(query)
        
        # Step 2: Vector search (threshold-based with safety cap)
        logger.debug(f"Performing vector search (max_chunks={settings.rag.max_chunks}, similarity>={threshold})")
        results = await self.db.vector_search(
            query_embedding=query_embedding,
            top_k=k,
            similarity_threshold=threshold,
            max_chunks=settings.rag.max_chunks
        )
        
        logger.info(f"Retrieved {len(results)} chunks (similarity >= {threshold}, capped at {settings.rag.max_chunks})")
        return results
    
    def _construct_prompt(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """Construct prompt with retrieved context."""
        # Format context from chunks
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            doc_title = chunk.get('document_title', 'Unknown')
            chunk_text = chunk['chunk_text']
            similarity = chunk.get('similarity_score', 0.0)
            
            context_parts.append(
                f"[Document {i}: {doc_title} (relevance: {similarity:.2f})]\n{chunk_text}"
            )
        
        context = "\n\n".join(context_parts)
        
        # Construct final prompt
        prompt = f"""You are a helpful AI assistant. Answer the user's question based on the provided context.

Context from retrieved documents:
{context}

User Question: {query}

Instructions:
- Answer the question using information from the context above
- If the context doesn't contain enough information, say so
- Be concise and accurate
- Cite which documents you used if relevant

Answer:"""
        
        return prompt
    
    async def generate(
        self,
        query: str,
        top_k: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate answer using naive RAG.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            temperature: LLM temperature
        
        Returns:
            Dictionary with answer, retrieved chunks, and metadata
        """
        if not self.db:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        # Step 1: Retrieve relevant chunks
        retrieved_chunks = await self.retrieve(query, top_k=top_k)
        
        if not retrieved_chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            return {
                'answer': "I couldn't find any relevant information to answer your question.",
                'retrieved_chunks': [],
                'chunk_ids': [],
                'latency_ms': 0,
                'error': 'No relevant chunks found'
            }
        
        # Step 2: Construct prompt
        prompt = self._construct_prompt(query, retrieved_chunks)
        
        # Step 3: Generate answer
        logger.debug("Generating answer with LLM")
        try:
            answer = await self.llm.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=settings.llm.max_tokens
            )
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return {
                'answer': "Error generating answer",
                'retrieved_chunks': retrieved_chunks,
                'chunk_ids': [c['chunk_id'] for c in retrieved_chunks],
                'latency_ms': 0,
                'error': str(e)
            }
        
        # Compute latency
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(f"Generated answer in {latency_ms:.2f}ms")
        
        return {
            'answer': answer,
            'retrieved_chunks': retrieved_chunks,
            'chunk_ids': [c['chunk_id'] for c in retrieved_chunks],
            'latency_ms': latency_ms,
            'rag_variant': 'naive',
            'query': query
        }
    
    async def batch_generate(
        self,
        queries: List[str],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Generate answers for multiple queries."""
        tasks = [self.generate(q, top_k=top_k) for q in queries]
        results = await asyncio.gather(*tasks)
        return results


# Example usage
if __name__ == "__main__":
    async def test_naive_rag():
        logging.basicConfig(level=logging.INFO)
        
        rag = NaiveRAG(top_k=3)
        await rag.initialize()
        
        query = "What is OpenAI's funding status?"
        result = await rag.generate(query)
        
        print(f"\nQuery: {query}")
        print(f"Answer: {result['answer']}")
        print(f"Retrieved {len(result['retrieved_chunks'])} chunks")
        print(f"Latency: {result['latency_ms']:.2f}ms")
    
    asyncio.run(test_naive_rag())
