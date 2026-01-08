"""
Embedding generation service with caching and batching.
"""

import asyncio
from typing import List, Union, Dict, Any
import logging
import hashlib
import json
from pathlib import Path

from src.utils.llm import get_embedder

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and caching embeddings."""
    
    def __init__(self, cache_dir: str = "./cache/embeddings", enable_cache: bool = True):
        self.cache_dir = Path(cache_dir)
        self.enable_cache = enable_cache
        self.embedder = None
        
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize the embedding provider."""
        if self.embedder is None:
            self.embedder = await get_embedder()
            logger.info("Embedding service initialized")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{cache_key}.json"
    
    async def _load_from_cache(self, text: str) -> Union[List[float], None]:
        """Load embedding from cache."""
        if not self.enable_cache:
            return None
        
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                return data['embedding']
            except Exception as e:
                logger.warning(f"Cache load error: {e}")
                return None
        
        return None
    
    async def _save_to_cache(self, text: str, embedding: List[float]):
        """Save embedding to cache."""
        if not self.enable_cache:
            return
        
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump({'text_preview': text[:100], 'embedding': embedding}, f)
        except Exception as e:
            logger.warning(f"Cache save error: {e}")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self.embedder:
            await self.initialize()
        
        # Check cache
        cached = await self._load_from_cache(text)
        if cached:
            logger.debug("Embedding loaded from cache")
            return cached
        
        # Generate embedding
        embedding = await self.embedder.embed(text)
        
        # Cache it
        await self._save_to_cache(text, embedding)
        
        return embedding
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts with caching."""
        if not self.embedder:
            await self.initialize()
        
        embeddings = []
        uncached_indices = []
        uncached_texts = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cached = await self._load_from_cache(text)
            if cached:
                embeddings.append(cached)
            else:
                embeddings.append(None)  # Placeholder
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            logger.info(f"Generating {len(uncached_texts)} embeddings (cache miss)")
            new_embeddings = await self.embedder.embed(uncached_texts)
            
            # Fill in placeholders and cache
            for idx, new_emb in zip(uncached_indices, new_embeddings):
                embeddings[idx] = new_emb
                await self._save_to_cache(texts[idx], new_emb)
        else:
            logger.info(f"All {len(texts)} embeddings loaded from cache")
        
        return embeddings
    
    async def embed_chunks(self, chunks: List[Any]) -> List[List[float]]:
        """Generate embeddings for chunk objects."""
        texts = [chunk.text for chunk in chunks]
        return await self.embed_batch(texts)


# Example
if __name__ == "__main__":
    async def test():
        service = EmbeddingService()
        
        texts = ["Hello world", "AI is amazing", "Hello world"]
        embeddings = await service.embed_batch(texts)
        
        print(f"Generated {len(embeddings)} embeddings")
        print(f"Embedding dimension: {len(embeddings[0])}")
    
    asyncio.run(test())
