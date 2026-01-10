"""
Configuration management using Pydantic Settings.
Centralized settings for the entire RAG benchmarking system.
"""

from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")
    
    url: str = Field(..., description="PostgreSQL connection URL")
    db: str = Field(default="rag_benchmark", description="Database name")
    user: str = Field(default="raguser", description="Database user")
    password: str = Field(..., description="Database password")
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")


class Neo4jSettings(BaseSettings):
    """Neo4j graph database configuration."""
    
    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", extra="ignore")
    
    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    user: str = Field(default="neo4j", description="Neo4j username")
    password: str = Field(..., description="Neo4j password")
    database: str = Field(default="neo4j", description="Neo4j database name")


class LLMSettings(BaseSettings):
    """LLM provider configuration."""
    
    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")
    
    provider: Literal["gemini", "openai", "ollama"] = Field(
        default="gemini",
        description="LLM provider to use"
    )
    model_name: str = Field(default="gemini-1.5-pro", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key for cloud providers")
    base_url: Optional[str] = Field(default=None, description="Base URL for API calls")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2048, ge=1, description="Maximum tokens to generate")
    timeout: int = Field(default=120, description="Request timeout in seconds")


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""
    
    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", env_file=".env", extra="ignore")
    
    provider: Literal["gemini", "openai", "ollama"] = Field(
        default="gemini",
        description="Embedding provider"
    )
    model_name: str = Field(default="text-embedding-004", description="Embedding model")
    dimensions: int = Field(default=768, ge=1, description="Embedding vector dimensions")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Base URL")
    batch_size: int = Field(default=100, ge=1, description="Batch size for embedding generation")


class IngestionSettings(BaseSettings):
    """Document ingestion configuration."""
    
    model_config = SettingsConfigDict(env_prefix="INGESTION_", env_file=".env", extra="ignore")
    
    chunk_size: int = Field(default=512, ge=1, description="Target chunk size in tokens")
    chunk_overlap: int = Field(default=50, ge=0, description="Overlap between chunks")
    max_chunk_size: int = Field(default=1024, ge=1, description="Maximum chunk size")
    use_semantic_chunking: bool = Field(default=True, description="Use semantic chunking")
    llm_model: str = Field(default="gemini-1.5-flash", description="LLM for graph building")


class BenchmarkSettings(BaseSettings):
    """Benchmark evaluation configuration."""
    
    model_config = SettingsConfigDict(env_prefix="BENCHMARK_", env_file=".env", extra="ignore")
    
    dataset_name: str = Field(default="factual_questions", description="Benchmark dataset name (without .json)")
    dataset_path: Optional[str] = Field(default=None, description="Explicit path to benchmark JSON file")
    datasets_dir: str = Field(default="./benchmarks/datasets", description="Directory containing benchmark datasets")
    num_questions: int = Field(default=50, ge=1, description="Number of questions to evaluate")
    batch_size: int = Field(default=10, ge=1, description="Batch size for processing")
    output_dir: str = Field(default="./benchmarks/results", description="Output directory")
    sample_seed: int = Field(default=42, description="Random seed for reproducibility")


class EvaluationSettings(BaseSettings):
    """LLM-based evaluation configuration."""
    
    model_config = SettingsConfigDict(env_prefix="EVAL_", env_file=".env", extra="ignore")
    
    llm_provider: Literal["gemini", "openai", "ollama"] = Field(
        default="gemini",
        description="LLM provider for scoring"
    )
    llm_model: str = Field(default="gemini-1.5-pro", description="Model for scoring")
    llm_api_key: Optional[str] = Field(default=None, description="API key")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Temperature for scoring")
    max_retries: int = Field(default=3, ge=1, description="Max retries for API calls")
    retry_delay: int = Field(default=2, ge=1, description="Delay between retries (seconds)")


class RAGSettings(BaseSettings):
    """RAG variant configuration."""
    
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")
    
    top_k: int = Field(default=5, ge=1, description="Number of chunks to retrieve")
    max_hops: int = Field(default=3, ge=1, le=10, description="Max hops for graph traversal")
    hybrid_fusion_strategy: Literal["rrf", "weighted", "concatenation"] = Field(
        default="rrf",
        description="Fusion strategy for hybrid RAG"
    )
    hybrid_vector_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Vector weight")
    hybrid_graph_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Graph weight")
    
    @field_validator("hybrid_graph_weight")
    @classmethod
    def validate_weights(cls, v, info):
        """Ensure weights sum to 1.0 for weighted strategy."""
        if info.data.get("hybrid_fusion_strategy") == "weighted":
            vector_weight = info.data.get("hybrid_vector_weight", 0.5)
            if abs(vector_weight + v - 1.0) > 0.001:
                raise ValueError("Vector and graph weights must sum to 1.0")
        return v


class AppSettings(BaseSettings):
    """Application-level configuration."""
    
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")
    
    env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: str = Field(default="./logs/app.log", description="Log file path")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    db_pool_size: int = Field(default=20, description="Database pool size")
    db_max_overflow: int = Field(default=10, description="Max overflow connections")
    db_pool_timeout: int = Field(default=30, description="Pool timeout")
    async_concurrency: int = Field(default=10, description="Max concurrent async operations")


class CacheSettings(BaseSettings):
    """Caching configuration."""
    
    model_config = SettingsConfigDict(env_prefix="CACHE_", env_file=".env", extra="ignore")
    
    enable_embedding_cache: bool = Field(default=True, description="Cache embeddings")
    dir: str = Field(default="./cache", description="Cache directory")
    ttl_hours: int = Field(default=24, ge=1, description="Cache TTL in hours")


class Settings(BaseSettings):
    """Main settings class aggregating all configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    benchmark: BenchmarkSettings = Field(default_factory=BenchmarkSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    
    def __init__(self, **kwargs):
        """Initialize settings with nested configuration."""
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.benchmark.output_dir,
            self.cache.dir,
            Path(self.app.log_file).parent,
            "./data/documents",
            "./benchmarks/datasets",
            "./benchmarks/results/figures",
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def postgres_url(self) -> str:
        """Get formatted PostgreSQL URL."""
        if "postgresql://" in self.database.url:
            return self.database.url
        return f"postgresql://{self.database.user}:{self.database.password}@{self.database.url}"
    
    def model_dump_json(self, **kwargs) -> str:
        """Serialize settings to JSON, masking sensitive data."""
        data = super().model_dump(**kwargs)
        # Mask sensitive fields
        if "database" in data and "password" in data["database"]:
            data["database"]["password"] = "***"
        if "neo4j" in data and "password" in data["neo4j"]:
            data["neo4j"]["password"] = "***"
        if "llm" in data and "api_key" in data["llm"]:
            data["llm"]["api_key"] = "***" if data["llm"]["api_key"] else None
        if "embedding" in data and "api_key" in data["embedding"]:
            data["embedding"]["api_key"] = "***" if data["embedding"]["api_key"] else None
        return data


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get global settings instance."""
    return settings


if __name__ == "__main__":
    # Test settings loading
    import json
    print("Settings loaded successfully!")
    print(json.dumps(settings.model_dump_json(), indent=2))
