# RAG Benchmarking System

## Overview

A benchmarking system comparing three RAG approaches for multi-hop question answering:

1. **Naive RAG**: Vector-based retrieval (PostgreSQL + pgvector)
2. **KG-RAG**: Knowledge Graph retrieval (Neo4j + Graphiti)
3. **Hybrid RAG**: Combined approach

## Goals

- Quantitative comparison of RAG architectures
- Evaluate multi-hop reasoning capabilities
- Generate actionable insights on when to use each approach

## System Architecture

```
Evaluation Orchestrator
    ↓       ↓       ↓
Naive  KG-RAG  Hybrid
  ↓       ↓       ↓
PostgreSQL Neo4j  Both
+pgvector +Graphiti
```

**Data Flow**:
1. **Ingestion**: Documents → Chunking → Dual storage (Vector + Graph)
2. **Evaluation**: Questions → 3 RAG variants → Answers
3. **Scoring**: LLM evaluates answers (5 dimensions, 1-10 scale)
4. **Analysis**: Statistical analysis + visualizations

## Evaluation Dimensions

| Dimension | Description |
|-----------|-------------|
| Correctness | Factual accuracy |
| Completeness | Full coverage |
| Relevance | Question alignment |
| Faithfulness | No hallucinations |
| Clarity | Clear expression |

## Technology Stack

**Infrastructure**: PostgreSQL 16 + pgvector, Neo4j 5, Docker  
**Python**: Pydantic AI, FastAPI, asyncpg, neo4j-driver, LangChain  
**LLMs**: Gemini (primary), Ollama (local)  
**Embeddings**: text-embedding-004 (Gemini)  
**Analysis**: Pandas, Matplotlib, Seaborn, Jupyter

## Datasets

Custom curated datasets focused on big tech AI industry:
- `big_tech_curated.json`: 255 questions (90 factual, 140 multi-hop, 25 analytical)
- `factual_questions.json`: Single-hop factual questions
- `analytical_questions.json`: Complex analytical questions
- `multihop_*.json`: Multi-hop reasoning questions

Source: 21 markdown documents covering AI investments, company strategies, executive movements, technology developments.

## Key Design Principles

- **Modularity**: Independent RAG implementations
- **Configurability**: Easy provider/model switching
- **Reproducibility**: Containerized, version-pinned
- **Observability**: Comprehensive logging and metrics
- **Cost-Awareness**: Local model support

## Output Artifacts

**During Execution**:
- `eval_*.json`: Responses from all RAG variants
- Detailed logging and metrics

**Post-Analysis**:
- Statistical reports
- Visualizations (box plots, radar charts)
- Comparative insights
