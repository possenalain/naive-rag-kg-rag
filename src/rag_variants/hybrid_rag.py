"""
Hybrid RAG: Combines vector similarity and knowledge graph retrieval.
Uses fusion strategies to merge results from both approaches.
"""

import asyncio
from typing import List, Dict, Any, Optional, Literal
import logging
from datetime import datetime

from src.rag_variants.naive_rag import NaiveRAG
from src.rag_variants.kg_rag import KnowledgeGraphRAG
from src.utils.llm import get_llm
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HybridRAG:
    """
    Hybrid RAG combining vector similarity and knowledge graph.
    
    Fusion Strategies:
    - RRF (Reciprocal Rank Fusion): Combines rankings from both methods
    - Weighted: Weighted combination of scores
    - Concatenation: Simply concatenate results from both methods
    """
    
    def __init__(
        self,
        top_k: Optional[int] = None,
        fusion_strategy: Optional[Literal["rrf", "weighted", "concatenation"]] = None,
        vector_weight: float = 0.5,
        graph_weight: float = 0.5
    ):
        """
        Args:
            top_k: Number of chunks to retrieve
            fusion_strategy: How to combine vector and graph results
            vector_weight: Weight for vector results (for weighted strategy)
            graph_weight: Weight for graph results (for weighted strategy)
        """
        self.top_k = top_k or settings.rag.top_k
        self.fusion_strategy = fusion_strategy or settings.rag.hybrid_fusion_strategy
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        
        # Initialize component RAG systems
        self.naive_rag = NaiveRAG(top_k=top_k)
        self.kg_rag = KnowledgeGraphRAG(top_k=top_k)
        self.llm = None
    
    async def initialize(self):
        """Initialize both RAG systems."""
        if self.llm is None:
            await self.naive_rag.initialize()
            await self.kg_rag.initialize()
            self.llm = await get_llm()
            logger.info("HybridRAG initialized")
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks using hybrid approach.
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
        
        Returns:
            Fused list of retrieved chunks
        """
        if not self.llm:
            await self.initialize()
        
        k = top_k or self.top_k
        
        # Retrieve from both methods in parallel
        logger.debug("Performing hybrid retrieval (vector + KG)")
        vector_results, kg_results = await asyncio.gather(
            self.naive_rag.retrieve(query, top_k=k),
            self.kg_rag.retrieve(query, top_k=k)
        )
        
        logger.info(f"Vector: {len(vector_results)} chunks, KG: {len(kg_results)} chunks")
        
        # Fuse results based on strategy
        if self.fusion_strategy == "rrf":
            fused_results = self._rrf_fusion(vector_results, kg_results, k)
        elif self.fusion_strategy == "weighted":
            fused_results = self._weighted_fusion(vector_results, kg_results, k)
        else:  # concatenation
            fused_results = self._concatenation_fusion(vector_results, kg_results, k)
        
        logger.info(f"Hybrid retrieval returned {len(fused_results)} chunks")
        return fused_results
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        top_k: int,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion.
        
        RRF score = 1 / (k + rank)
        """
        chunk_scores = {}
        
        # Score vector results
        for rank, chunk in enumerate(vector_results, start=1):
            chunk_id = chunk['chunk_id']
            rrf_score = 1.0 / (rrf_k + rank)
            
            chunk_scores[chunk_id] = {
                'chunk': chunk,
                'vector_rank': rank,
                'rrf_score': rrf_score,
                'sources': ['vector']
            }
        
        # Add KG results
        for rank, chunk in enumerate(kg_results, start=1):
            chunk_id = chunk['chunk_id']
            rrf_score = 1.0 / (rrf_k + rank)
            
            if chunk_id in chunk_scores:
                # Chunk appears in both - boost score
                chunk_scores[chunk_id]['rrf_score'] += rrf_score
                chunk_scores[chunk_id]['sources'].append('kg')
                chunk_scores[chunk_id]['kg_rank'] = rank
            else:
                chunk_scores[chunk_id] = {
                    'chunk': chunk,
                    'kg_rank': rank,
                    'rrf_score': rrf_score,
                    'sources': ['kg']
                }
        
        # Sort by RRF score and return top-k
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )[:top_k]
        
        # Format results
        results = []
        for item in sorted_chunks:
            chunk = item['chunk'].copy()
            chunk['fusion_score'] = item['rrf_score']
            chunk['retrieval_sources'] = item['sources']
            chunk['fusion_strategy'] = 'rrf'
            results.append(chunk)
        
        logger.debug(f"RRF fusion: {len(results)} unique chunks")
        return results
    
    def _weighted_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Weighted fusion using scores from each method.
        """
        chunk_scores = {}
        
        # Score vector results
        for chunk in vector_results:
            chunk_id = chunk['chunk_id']
            # Normalize similarity score (already 0-1)
            vector_score = chunk.get('similarity_score', 0.5)
            
            chunk_scores[chunk_id] = {
                'chunk': chunk,
                'weighted_score': vector_score * self.vector_weight,
                'sources': ['vector']
            }
        
        # Add KG results
        for chunk in kg_results:
            chunk_id = chunk['chunk_id']
            # Normalize relevance score
            kg_score = chunk.get('relevance_score', 1.0) / 10.0  # Assume max 10
            
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]['weighted_score'] += kg_score * self.graph_weight
                chunk_scores[chunk_id]['sources'].append('kg')
            else:
                chunk_scores[chunk_id] = {
                    'chunk': chunk,
                    'weighted_score': kg_score * self.graph_weight,
                    'sources': ['kg']
                }
        
        # Sort and return top-k
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x['weighted_score'],
            reverse=True
        )[:top_k]
        
        results = []
        for item in sorted_chunks:
            chunk = item['chunk'].copy()
            chunk['fusion_score'] = item['weighted_score']
            chunk['retrieval_sources'] = item['sources']
            chunk['fusion_strategy'] = 'weighted'
            results.append(chunk)
        
        logger.debug(f"Weighted fusion: {len(results)} unique chunks")
        return results
    
    def _concatenation_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Simple concatenation with deduplication.
        Prioritizes vector results, then adds KG results.
        """
        seen_chunk_ids = set()
        results = []
        
        # Add vector results first
        for chunk in vector_results:
            chunk_id = chunk['chunk_id']
            if chunk_id not in seen_chunk_ids:
                chunk_copy = chunk.copy()
                chunk_copy['retrieval_sources'] = ['vector']
                chunk_copy['fusion_strategy'] = 'concatenation'
                results.append(chunk_copy)
                seen_chunk_ids.add(chunk_id)
                
                if len(results) >= top_k:
                    break
        
        # Add KG results
        for chunk in kg_results:
            chunk_id = chunk['chunk_id']
            if chunk_id not in seen_chunk_ids:
                chunk_copy = chunk.copy()
                chunk_copy['retrieval_sources'] = ['kg']
                chunk_copy['fusion_strategy'] = 'concatenation'
                results.append(chunk_copy)
                seen_chunk_ids.add(chunk_id)
                
                if len(results) >= top_k:
                    break
        
        logger.debug(f"Concatenation fusion: {len(results)} unique chunks")
        return results[:top_k]
    
    def _construct_prompt(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """Construct prompt with hybrid context."""
        context_parts = []
        
        for i, chunk in enumerate(retrieved_chunks, 1):
            chunk_text = chunk['chunk_text']
            sources = ', '.join(chunk.get('retrieval_sources', ['unknown']))
            fusion_score = chunk.get('fusion_score', 0.0)
            
            context_parts.append(
                f"[Context {i} - Sources: {sources}, Score: {fusion_score:.3f}]\n{chunk_text}"
            )
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""You are a helpful AI assistant with access to both vector similarity search and a knowledge graph. Answer the user's question based on the provided context, which has been retrieved using a hybrid approach combining both methods.

Hybrid Context (Vector + Knowledge Graph):
{context}

User Question: {query}

Instructions:
- Answer using information from the hybrid context
- The context combines results from semantic similarity and graph relationships
- Synthesize information across different sources
- If the context doesn't contain enough information, say so
- Be concise and accurate

Answer:"""
        
        return prompt
    
    async def generate(
        self,
        query: str,
        top_k: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate answer using Hybrid RAG.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            temperature: LLM temperature
        
        Returns:
            Dictionary with answer, retrieved chunks, and metadata
        """
        if not self.llm:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        # Step 1: Hybrid retrieval
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
            'rag_variant': 'hybrid',
            'fusion_strategy': self.fusion_strategy,
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
    async def test_hybrid_rag():
        logging.basicConfig(level=logging.INFO)
        
        rag = HybridRAG(top_k=5, fusion_strategy="rrf")
        await rag.initialize()
        
        query = "How is AI funding evolving across major tech companies?"
        result = await rag.generate(query)
        
        print(f"\nQuery: {query}")
        print(f"Answer: {result['answer']}")
        print(f"Retrieved {len(result['retrieved_chunks'])} chunks (fusion: {result['fusion_strategy']})")
        print(f"Latency: {result['latency_ms']:.2f}ms")
    
    asyncio.run(test_hybrid_rag())
