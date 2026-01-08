"""RAG Benchmarking System - Main package."""

__version__ = "0.1.0"
__author__ = "RAG Research Team"

# Main exports
from src.ingestion.pipeline import IngestionPipeline
from src.rag_variants.naive_rag import NaiveRAG
from src.rag_variants.kg_rag import KnowledgeGraphRAG
from src.rag_variants.hybrid_rag import HybridRAG
from src.evaluation.orchestrator import EvaluationOrchestrator

__all__ = [
    'IngestionPipeline',
    'NaiveRAG',
    'KnowledgeGraphRAG',
    'HybridRAG',
    'EvaluationOrchestrator'
]
