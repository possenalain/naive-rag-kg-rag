"""
Hybrid RAG: Combines vector similarity and knowledge graph retrieval.
Uses fusion strategies to merge results from both approaches.

IMPORTANT - Score Normalization:
- Vector scores: Already normalized 0-1 (cosine similarity), filtered at threshold (e.g., 0.7+)
- KG scores: Raw values from (weighted_count² × recall × boost) typically 10-80
- Fusion normalization: DYNAMIC range mapping
  * Calculates actual min/max from current vector and KG results
  * Maps KG range -> vector range to ensure equal weighting
  * Adapts to different query patterns and scoring configurations
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
    - Adaptive: Combines RRF (robust rank-based) + weighted scores (value-based)
    - Concatenation: Simply concatenate results from both methods
    """
    
    def __init__(
        self,
        top_k: Optional[int] = None,
        fusion_strategy: Optional[Literal["rrf", "weighted", "adaptive", "concatenation"]] = None,
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
            top_k: Number of chunks to retrieve (deprecated, uses max_chunks for threshold-based retrieval)
        
        Returns:
            Fused list of retrieved chunks
        """
        if not self.llm:
            await self.initialize()
        
        k = top_k or self.top_k
        max_chunks = settings.rag.max_chunks
        
        # Retrieve from both methods in parallel (they use max_chunks internally)
        logger.debug("Performing hybrid retrieval (vector + KG)")
        vector_results, kg_results = await asyncio.gather(
            self.naive_rag.retrieve(query, top_k=k),
            self.kg_rag.retrieve(query, top_k=k)
        )
        
        logger.info(f"Vector: {len(vector_results)} chunks, KG: {len(kg_results)} chunks")
        
        # Fuse results based on strategy (use max_chunks for fusion limit)
        if self.fusion_strategy == "rrf":
            fused_results = self._rrf_fusion(vector_results, kg_results, max_chunks)
        elif self.fusion_strategy == "weighted":
            fused_results = self._weighted_fusion(vector_results, kg_results, max_chunks)
        elif self.fusion_strategy == "adaptive":
            fused_results = self._adaptive_fusion(vector_results, kg_results, max_chunks)
        else:  # concatenation
            fused_results = self._concatenation_fusion(vector_results, kg_results, max_chunks)
        
        # Count source composition of final results
        vector_only = 0
        kg_only = 0
        both = 0
        vector_total_score = 0
        kg_total_score = 0
        
        for chunk in fused_results:
            sources = chunk.get('retrieval_sources', [])
            fusion_score = chunk.get('fusion_score', 0)
            
            if len(sources) == 2 or (len(sources) == 1 and 'both' in sources):
                both += 1
                # For chunks in both, score is shared
                vector_total_score += fusion_score / 2
                kg_total_score += fusion_score / 2
            elif 'vector' in sources:
                vector_only += 1
                vector_total_score += fusion_score
            elif 'kg' in sources:
                kg_only += 1
                kg_total_score += fusion_score
        
        total_score = vector_total_score + kg_total_score
        vector_pct = (vector_total_score / total_score * 100) if total_score > 0 else 0
        kg_pct = (kg_total_score / total_score * 100) if total_score > 0 else 0
        
        logger.info(
            f"Hybrid retrieval returned {len(fused_results)} chunks "
            f"(vector_only={vector_only}, kg_only={kg_only}, both={both}) | "
            f"Score contribution: vector={vector_pct:.1f}%, kg={kg_pct:.1f}%"
        )
        return fused_results
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        max_chunks: int,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion.
        
        RRF score = 1 / (k + rank)
        Returns all fused chunks up to max_chunks limit.
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
        
        # Sort by RRF score and return up to max_chunks
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )[:max_chunks]
        
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
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """
        Weighted fusion using scores from each method.
        Uses dynamic normalization to map KG scores to vector score range.
        Returns all fused chunks up to max_chunks limit.
        """
        chunk_scores = {}
        
        # Get vector score range for normalization target
        vector_scores = [c.get('similarity_score', 0.5) for c in vector_results]
        vector_min = min(vector_scores) if vector_scores else 0.7
        vector_max = max(vector_scores) if vector_scores else 1.0
        
        # Get KG score range for normalization source
        kg_raw_scores = [c.get('relevance_score', 1.0) for c in kg_results]
        if kg_raw_scores:
            kg_min = min(kg_raw_scores)
            kg_max = max(kg_raw_scores)
            kg_range = kg_max - kg_min
            
            # Handle zero range: use vector mean instead of vector_min
            if kg_range == 0:
                kg_fallback_score = (vector_min + vector_max) / 2
                logger.debug(f"Zero KG range detected, using vector mean {kg_fallback_score:.3f} for all KG scores")
        else:
            kg_min, kg_max, kg_range = 10.0, 80.0, 70.0  # Fallback
            kg_fallback_score = None
        
        logger.debug(
            f"Score ranges - Vector: [{vector_min:.2f}, {vector_max:.2f}], "
            f"KG: [{kg_min:.2f}, {kg_max:.2f}]"
        )
        
        # Score vector results
        for chunk in vector_results:
            chunk_id = chunk['chunk_id']
            vector_score = chunk.get('similarity_score', 0.5)
            
            chunk_scores[chunk_id] = {
                'chunk': chunk,
                'weighted_score': vector_score * self.vector_weight,
                'sources': ['vector']
            }
        
        # Add KG results with dynamic normalization
        for chunk in kg_results:
            chunk_id = chunk['chunk_id']
            kg_raw = chunk.get('relevance_score', 1.0)
            
            # Handle zero range edge case
            if kg_range == 0:
                kg_score = kg_fallback_score
            else:
                # Map KG score range to vector score range dynamically
                kg_normalized = vector_min + ((kg_raw - kg_min) / kg_range) * (vector_max - vector_min)
                kg_score = max(min(kg_normalized, 1.0), 0.0)  # Clamp to [0, 1]
            
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]['weighted_score'] += kg_score * self.graph_weight
                chunk_scores[chunk_id]['sources'].append('kg')
            else:
                chunk_scores[chunk_id] = {
                    'chunk': chunk,
                    'weighted_score': kg_score * self.graph_weight,
                    'sources': ['kg']
                }
        
        # Sort and return up to max_chunks
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x['weighted_score'],
            reverse=True
        )[:max_chunks]
        
        results = []
        for item in sorted_chunks:
            chunk = item['chunk'].copy()
            chunk['fusion_score'] = item['weighted_score']
            chunk['retrieval_sources'] = item['sources']
            chunk['fusion_strategy'] = 'weighted'
            results.append(chunk)
        
        logger.debug(f"Weighted fusion: {len(results)} unique chunks")
        return results
    
    def _adaptive_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        max_chunks: int,
        rrf_k: int = 60,
        weight_alpha: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Adaptive fusion: Combines RRF (rank robustness) + weighted scores (value precision).
        
        Final score = RRF_score + (weighted_score * alpha)
        - RRF provides rank-based robustness (no normalization needed)
        - Weighted scores add value-based signal from similarity/relevance
        - Alpha balances contribution (default 0.3 = RRF dominant)
        - Uses dynamic normalization to map KG scores to vector score range
        Returns all fused chunks up to max_chunks limit.
        """
        chunk_scores = {}
        
        # Get score ranges for dynamic normalization
        vector_scores_list = [c.get('similarity_score', 0.5) for c in vector_results]
        kg_raw_scores = [c.get('relevance_score', 1.0) for c in kg_results]
        
        vector_min = min(vector_scores_list) if vector_scores_list else 0.7
        vector_max = max(vector_scores_list) if vector_scores_list else 1.0
        
        if kg_raw_scores:
            kg_min = min(kg_raw_scores)
            kg_max = max(kg_raw_scores)
            kg_range = kg_max - kg_min
            
            # Handle zero range: use vector mean instead of vector_min
            if kg_range == 0:
                kg_fallback_score = (vector_min + vector_max) / 2
                logger.debug(f"Zero KG range in adaptive fusion, using vector mean {kg_fallback_score:.3f}")
        else:
            kg_min, kg_max, kg_range = 10.0, 80.0, 70.0  # Fallback
            kg_fallback_score = None
        
        logger.debug(
            f"Adaptive fusion score ranges - Vector: [{vector_min:.2f}, {vector_max:.2f}], "
            f"KG: [{kg_min:.2f}, {kg_max:.2f}]"
        )
        
        # Process vector results: RRF + weighted score
        for rank, chunk in enumerate(vector_results, start=1):
            chunk_id = chunk['chunk_id']
            rrf_score = 1.0 / (rrf_k + rank)
            vector_score = chunk.get('similarity_score', 0.5)  # Already 0-1
            weighted_score = vector_score * self.vector_weight
            
            chunk_scores[chunk_id] = {
                'chunk': chunk,
                'rrf_score': rrf_score,
                'weighted_score': weighted_score,
                'vector_rank': rank,
                'vector_score': vector_score,
                'sources': ['vector']
            }
        
        # Process KG results: RRF + weighted score with dynamic normalization
        for rank, chunk in enumerate(kg_results, start=1):
            chunk_id = chunk['chunk_id']
            rrf_score = 1.0 / (rrf_k + rank)
            kg_raw_score = chunk.get('relevance_score', 1.0)
            
            # Handle zero range edge case
            if kg_range == 0:
                kg_normalized = kg_fallback_score
            else:
                # Map KG score range to vector score range dynamically
                kg_normalized = vector_min + ((kg_raw_score - kg_min) / kg_range) * (vector_max - vector_min)
                kg_normalized = max(min(kg_normalized, 1.0), 0.0)  # Clamp to [0, 1]
            
            weighted_score = kg_normalized * self.graph_weight
            
            if chunk_id in chunk_scores:
                # Appears in BOTH: Add RRF scores + combine weighted scores
                chunk_scores[chunk_id]['rrf_score'] += rrf_score
                chunk_scores[chunk_id]['weighted_score'] += weighted_score
                chunk_scores[chunk_id]['sources'].append('kg')
                chunk_scores[chunk_id]['kg_rank'] = rank
                chunk_scores[chunk_id]['kg_score'] = kg_normalized
            else:
                chunk_scores[chunk_id] = {
                    'chunk': chunk,
                    'rrf_score': rrf_score,
                    'weighted_score': weighted_score,
                    'kg_rank': rank,
                    'kg_score': kg_normalized,
                    'sources': ['kg']
                }
        
        # Calculate final adaptive scores: RRF + (weighted * alpha)
        for chunk_id, data in chunk_scores.items():
            data['adaptive_score'] = data['rrf_score'] + (data['weighted_score'] * weight_alpha)
        
        # Sort by adaptive score and return up to max_chunks
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x['adaptive_score'],
            reverse=True
        )[:max_chunks]
        
        # Format results
        results = []
        for item in sorted_chunks:
            chunk = item['chunk'].copy()
            chunk['fusion_score'] = item['adaptive_score']
            chunk['rrf_component'] = item['rrf_score']
            chunk['weighted_component'] = item['weighted_score']
            chunk['retrieval_sources'] = item['sources']
            chunk['fusion_strategy'] = 'adaptive'
            results.append(chunk)
        
        logger.debug(
            f"Adaptive fusion: {len(results)} chunks "
            f"(avg RRF={sum(r['rrf_component'] for r in results)/len(results):.4f}, "
            f"avg weighted={sum(r['weighted_component'] for r in results)/len(results):.4f})"
        )
        return results
    
    def _concatenation_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """
        Simple concatenation with deduplication.
        Prioritizes vector results, then adds KG results.
        Returns all unique chunks up to max_chunks limit.
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
                
                if len(results) >= max_chunks:
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
                
                if len(results) >= max_chunks:
                    break
        
        logger.debug(f"Concatenation fusion: {len(results)} unique chunks")
        return results[:max_chunks]
    
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
