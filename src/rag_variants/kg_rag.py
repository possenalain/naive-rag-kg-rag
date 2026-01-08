"""
Knowledge Graph RAG: Retrieval via knowledge graph traversal.
Uses entity extraction and graph relationships.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.utils.graph import get_graph
from src.utils.db import get_db
from src.utils.llm import get_llm
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class KnowledgeGraphRAG:
    """
    Knowledge Graph RAG implementation.
    
    Pipeline:
    1. Extract entities from user query (implicit in Graphiti search)
    2. Find relevant entities in knowledge graph
    3. Traverse graph to find connected chunks
    4. Rank and retrieve top-k chunks
    5. Generate answer using LLM
    """
    
    def __init__(
        self,
        top_k: Optional[int] = None,
        max_hops: Optional[int] = None
    ):
        """
        Args:
            top_k: Number of chunks to retrieve
            max_hops: Maximum hops for graph traversal
        """
        self.top_k = top_k or settings.rag.top_k
        self.max_hops = max_hops or settings.rag.max_hops
        self.graph = None
        self.db = None
        self.llm = None
    
    async def initialize(self):
        """Initialize graph database and LLM connections."""
        if self.graph is None:
            self.graph = await get_graph()
            self.db = await get_db()
            self.llm = await get_llm()
            logger.info("KnowledgeGraphRAG initialized")
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        max_hops: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks via knowledge graph.
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            max_hops: Max hops for traversal
        
        Returns:
            List of retrieved chunks with metadata
        """
        if not self.graph:
            await self.initialize()
        
        k = top_k or self.top_k
        hops = max_hops or self.max_hops
        
        # Use Graphiti's knowledge graph retrieval
        logger.debug(f"Performing KG retrieval (top_k={k}, max_hops={hops})")
        results = await self.graph.kg_retrieve(
            query_text=query,
            top_k=k,
            max_hops=hops
        )
        
        # Enrich with document metadata from PostgreSQL
        enriched_results = []
        for result in results:
            chunk_id = result['chunk_id']
            
            # Get full chunk data from PostgreSQL
            chunk_data = await self.db.get_chunk(chunk_id)
            if chunk_data:
                enriched_results.append({
                    **result,
                    'metadata': chunk_data.get('metadata', {}),
                    'retrieval_score': result.get('relevance_score', 1.0)
                })
        
        logger.info(f"Retrieved {len(enriched_results)} chunks via KG")
        return enriched_results
    
    def _construct_prompt(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """Construct prompt with retrieved context from KG."""
        # Format context from chunks
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            chunk_text = chunk['chunk_text']
            relevance = chunk.get('retrieval_score', 1.0)
            
            # Note: These are connected via knowledge graph
            context_parts.append(
                f"[Context {i} (KG relevance: {relevance})]\n{chunk_text}"
            )
        
        context = "\n\n".join(context_parts)
        
        # Construct final prompt
        prompt = f"""You are a helpful AI assistant with access to a knowledge graph. Answer the user's question based on the provided context, which has been retrieved through semantic relationships in the knowledge graph.

Context from knowledge graph:
{context}

User Question: {query}

Instructions:
- Answer the question using information from the knowledge graph context
- The context chunks are connected through entities and relationships
- If the context doesn't contain enough information, say so
- Be concise, accurate, and synthesize information across chunks
- Note connections between different pieces of information when relevant

Answer:"""
        
        return prompt
    
    async def generate(
        self,
        query: str,
        top_k: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate answer using Knowledge Graph RAG.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            temperature: LLM temperature
        
        Returns:
            Dictionary with answer, retrieved chunks, and metadata
        """
        if not self.graph:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        # Step 1: Retrieve via knowledge graph
        retrieved_chunks = await self.retrieve(query, top_k=top_k)
        
        if not retrieved_chunks:
            logger.warning(f"No relevant chunks found for query: {query}")
            return {
                'answer': "I couldn't find any relevant information in the knowledge graph to answer your question.",
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
            'rag_variant': 'kg',
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
    async def test_kg_rag():
        logging.basicConfig(level=logging.INFO)
        
        rag = KnowledgeGraphRAG(top_k=3, max_hops=2)
        await rag.initialize()
        
        query = "What is the relationship between OpenAI and Microsoft?"
        result = await rag.generate(query)
        
        print(f"\nQuery: {query}")
        print(f"Answer: {result['answer']}")
        print(f"Retrieved {len(result['retrieved_chunks'])} chunks via KG")
        print(f"Latency: {result['latency_ms']:.2f}ms")
    
    asyncio.run(test_kg_rag())
