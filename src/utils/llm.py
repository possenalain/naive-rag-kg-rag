"""
LLM provider abstraction layer supporting multiple providers.
Provides unified interface for text generation and embeddings.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import asyncio
import logging
from enum import Enum
from google import genai
from openai import AsyncOpenAI
import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    OLLAMA = "ollama"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Generate text completion."""
        pass
    
    @abstractmethod
    async def embed(
        self,
        texts: Union[str, List[str]],
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text(s)."""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Chat completion with message history."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-pro",
        embedding_model: str = "text-embedding-004"
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.embedding_model = embedding_model
        logger.info(f"Initialized Gemini provider with model: {model_name}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Generate text using Gemini."""
        try:
            # Combine system prompt with user prompt
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            # Generate using new API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Chat completion with Gemini."""
        try:
            # Convert messages to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(genai.types.Content(
                    role=role,
                    parts=[genai.types.Part(text=msg["content"])]
                ))
            
            # Generate response
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise
    
    async def embed(
        self,
        texts: Union[str, List[str]],
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using Gemini."""
        try:
            is_single = isinstance(texts, str)
            text_list = [texts] if is_single else texts
            
            # Batch embed
            embeddings = []
            batch_size = settings.embedding.batch_size
            
            for i in range(0, len(text_list), batch_size):
                batch = text_list[i:i + batch_size]
                
                # Use new API for batch embedding
                for text in batch:
                    result = self.client.models.embed_content(
                        model=self.embedding_model,
                        contents=text,
                    )
                    embeddings.append(result.embeddings[0].values)
            
            return embeddings[0] if is_single else embeddings
            
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small"
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        self.embedding_model = embedding_model
        logger.info(f"Initialized OpenAI provider with model: {model_name}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Generate text using OpenAI."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Chat completion with OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise
    
    async def embed(
        self,
        texts: Union[str, List[str]],
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using OpenAI."""
        try:
            is_single = isinstance(texts, str)
            text_list = [texts] if is_single else texts
            
            # Batch embed
            embeddings = []
            batch_size = settings.embedding.batch_size
            
            for i in range(0, len(text_list), batch_size):
                batch = text_list[i:i + batch_size]
                
                response = await self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings[0] if is_single else embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider implementation."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.2",
        embedding_model: str = "nomic-embed-text"
    ):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(timeout=120.0)
        logger.info(f"Initialized Ollama provider with model: {model_name}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Generate text using Ollama."""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Chat completion with Ollama."""
        try:
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def embed(
        self,
        texts: Union[str, List[str]],
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using Ollama."""
        try:
            is_single = isinstance(texts, str)
            text_list = [texts] if is_single else texts
            
            embeddings = []
            for text in text_list:
                payload = {
                    "model": self.embedding_model,
                    "prompt": text
                }
                
                response = await self.client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                embeddings.append(result.get("embedding", []))
            
            return embeddings[0] if is_single else embeddings
            
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


class LLMFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def create_llm_provider(
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """Create an LLM provider instance."""
        provider = provider or settings.llm.provider
        
        if provider == LLMProvider.GEMINI:
            api_key = kwargs.get("api_key") or settings.llm.api_key
            model_name = kwargs.get("model_name") or settings.llm.model_name
            return GeminiProvider(api_key=api_key, model_name=model_name)
        
        elif provider == LLMProvider.OPENAI:
            api_key = kwargs.get("api_key") or settings.llm.api_key
            model_name = kwargs.get("model_name") or settings.llm.model_name
            return OpenAIProvider(api_key=api_key, model_name=model_name)
        
        elif provider == LLMProvider.OLLAMA:
            base_url = kwargs.get("base_url") or settings.llm.base_url or "http://localhost:11434"
            model_name = kwargs.get("model_name") or settings.llm.model_name
            return OllamaProvider(base_url=base_url, model_name=model_name)
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_embedding_provider(
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """Create an embedding provider instance."""
        provider = provider or settings.embedding.provider
        
        if provider == LLMProvider.GEMINI:
            api_key = kwargs.get("api_key") or settings.embedding.api_key
            embedding_model = kwargs.get("embedding_model") or settings.embedding.model_name
            return GeminiProvider(
                api_key=api_key,
                model_name=settings.llm.model_name,  # For generation
                embedding_model=embedding_model
            )
        
        elif provider == LLMProvider.OPENAI:
            api_key = kwargs.get("api_key") or settings.embedding.api_key
            embedding_model = kwargs.get("embedding_model") or settings.embedding.model_name
            return OpenAIProvider(
                api_key=api_key,
                model_name=settings.llm.model_name,
                embedding_model=embedding_model
            )
        
        elif provider == LLMProvider.OLLAMA:
            base_url = kwargs.get("base_url") or settings.embedding.base_url or "http://localhost:11434"
            embedding_model = kwargs.get("embedding_model") or settings.embedding.model_name
            return OllamaProvider(
                base_url=base_url,
                model_name=settings.llm.model_name,
                embedding_model=embedding_model
            )
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")


# Convenience functions
async def get_llm() -> BaseLLMProvider:
    """Get LLM provider instance."""
    return LLMFactory.create_llm_provider()


async def get_embedder() -> BaseLLMProvider:
    """Get embedding provider instance."""
    return LLMFactory.create_embedding_provider()


# Example usage
if __name__ == "__main__":
    async def test_providers():
        # Test Gemini
        llm = LLMFactory.create_llm_provider(LLMProvider.GEMINI)
        result = await llm.generate("What is 2+2?")
        print(f"Gemini: {result}")
        
        # Test embeddings
        embedder = LLMFactory.create_embedding_provider(LLMProvider.GEMINI)
        embedding = await embedder.embed("Hello world")
        print(f"Embedding dim: {len(embedding)}")
    
    asyncio.run(test_providers())
