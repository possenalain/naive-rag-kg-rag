# Technical Architecture

System architecture for RAG benchmarking comparing Naive RAG, KG-RAG, and Hybrid RAG.

## System Layers

```
┌────────────────────────────────────┐
│      CLI / Notebooks / API          │  Presentation
└────────────────────────────────────┘
              ↓
┌────────────────────────────────────┐
│    Evaluation Orchestrator          │  Orchestration
│  - Routes questions to RAG variants │
│  - Collects responses & metrics     │
└────────────────────────────────────┘
              ↓
┌──────────┬───────────┬─────────────┐
│ Naive    │  KG-RAG   │  Hybrid     │  RAG Variants
│ RAG      │           │  RAG        │
└──────────┴───────────┴─────────────┘
      ↓          ↓           ↓
┌──────────┬───────────┬─────────────┐
│PostgreSQL│  Neo4j    │   Both      │  Storage
│+pgvector │ +Graphiti │             │
└──────────┴───────────┴─────────────┘
```

## Core Components

### 1. Ingestion Pipeline

**Flow**: Document → Chunking → Dual Path Storage

```python
Document Loader
    ↓
Semantic Chunker (512 tokens, 50 overlap)
    ↓
    ├─→ Embedding → PostgreSQL (Vector)
    └─→ Entity/Relation Extraction → Neo4j (Graph)
```

**Key Classes**:
- `DocumentLoader`: Load and parse documents
- `SemanticChunker`: Intelligent text chunking
- `EmbeddingService`: Generate embeddings
- `GraphBuilder`: Extract entities and relationships

### 2. RAG Variants

#### Naive RAG
**Flow**: Query → Embedding → Vector Search → LLM

```python
class NaiveRAG:
    async def retrieve(query: str) -> List[Chunk]:
        # 1. Embed query
        vector = await embed(query)
        # 2. Similarity search
        chunks = await vector_store.search(vector, top_k=5)
        return chunks
    
    async def generate(query: str, chunks: List[Chunk]) -> str:
        context = format_chunks(chunks)
        return await llm.generate(prompt(query, context))
```

**Strengths**: Fast, simple, good baseline  
**Weaknesses**: Limited multi-hop reasoning

#### KG-RAG
**Flow**: Query → Entity Extraction → Graph Traversal → LLM

```python
class KgRAG:
    async def retrieve(query: str) -> Subgraph:
        # 1. Extract entities from query
        entities = await extract_entities(query)
        # 2. Traverse graph (2-3 hops)
        subgraph = await graph.traverse(entities, max_hops=3)
        return subgraph
    
    async def generate(query: str, subgraph: Subgraph) -> str:
        context = format_graph(subgraph)
        return await llm.generate(prompt(query, context))
```

**Strengths**: Excellent multi-hop, captures relationships  
**Weaknesses**: Slower, more complex

#### Hybrid RAG
**Flow**: Query → Parallel(Vector + Graph) → Fusion → LLM

```python
class HybridRAG:
    async def retrieve(query: str) -> List[Context]:
        # 1. Parallel retrieval
        vector_results, graph_results = await asyncio.gather(
            naive_rag.retrieve(query),
            kg_rag.retrieve(query)
        )
        # 2. Fusion with normalization
        fused = await fusion_scorer.fuse(vector_results, graph_results)
        return fused
    
    async def generate(query: str, contexts: List[Context]) -> str:
        context = format_hybrid(contexts)
        return await llm.generate(prompt(query, context))
```

**Strengths**: Combines both approaches  
**Weaknesses**: Highest latency

### 3. Evaluation System

**Flow**: Questions → RAG Variants → Scoring → Analysis

```python
class EvaluationOrchestrator:
    async def run_evaluation(dataset: str):
        # 1. Load questions from custom dataset
        questions = load_dataset(dataset)  # e.g., big_tech_curated
        
        # 2. Execute all RAG variants
        for q in questions:
            results = await asyncio.gather(
                naive_rag.run(q),
                kg_rag.run(q),
                hybrid_rag.run(q)
            )
            save_results(results)
        
        # 3. Score answers
        scores = await score_with_llm(results)
        save_scores(scores)
        
        # 4. Analyze
        generate_statistics(scores)
        generate_visualizations(scores)
```

**Scoring Dimensions** (1-10 scale):
- Correctness: Factual accuracy
- Completeness: Full coverage
- Relevance: Question alignment
- Faithfulness: No hallucinations
- Clarity: Expression quality

### 4. Data Stores

#### PostgreSQL + pgvector
```sql
-- Chunks table with vector embeddings
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID,
    content TEXT,
    embedding vector(768),
    metadata JSONB
);

-- Vector similarity search
SELECT * FROM chunks
ORDER BY embedding <=> query_vector
LIMIT 5;
```

#### Neo4j + Graphiti
```cypher
// Entity and relationship structure
(:Entity {name, type, ...})-[:RELATES_TO]->(:Entity)
(:Chunk {content, ...})-[:MENTIONS]->(:Entity)

// Example traversal
MATCH (e:Entity {name: $entity})-[r*1..3]->(related:Entity)
RETURN e, r, related
```

## Key Design Patterns

### Fusion Scoring
Combines vector and graph results with normalized scores:

```python
def fused_score(vector_score, graph_score, alpha=0.5):
    # Normalize scores to [0, 1]
    norm_v = normalize_vector_score(vector_score)
    norm_g = normalize_graph_score(graph_score)
    
    # Weighted combination
    return alpha * norm_v + (1 - alpha) * norm_g
```

### Async Processing
All I/O operations use async/await for parallelization:

```python
# Parallel embedding generation
embeddings = await asyncio.gather(*[
    embed_text(chunk) for chunk in chunks
])

# Parallel RAG execution
results = await asyncio.gather(
    naive_rag.run(query),
    kg_rag.run(query),
    hybrid_rag.run(query)
)
```

### Caching
Embeddings cached to avoid regeneration:

```python
@cache_embeddings
async def embed_text(text: str) -> Vector:
    # Check cache first
    if cached := get_cached_embedding(text):
        return cached
    # Generate and cache
    embedding = await embedding_service.embed(text)
    cache_embedding(text, embedding)
    return embedding
```

## Configuration

### Environment Variables
```bash
# Database
POSTGRES_URL=postgresql://raguser:pwd@localhost:5432/rag_benchmark
NEO4J_URI=bolt://localhost:7687

# LLM
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-1.5-pro

# Embedding
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL_NAME=text-embedding-004
EMBEDDING_DIMENSIONS=768

# RAG Settings
NAIVE_TOP_K=5
KG_MAX_HOPS=3
HYBRID_ALPHA=0.5
```

### Settings Management
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_url: str
    neo4j_uri: str
    llm_provider: str
    embedding_dimensions: int = 768
    
    class Config:
        env_file = ".env"
```

## Infrastructure

### Docker Compose
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: rag_benchmark
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  neo4j:
    image: neo4j:5.15
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data
```

## Performance Considerations

**Latency Comparison** (typical):
- Naive RAG: ~1-2s per query
- KG-RAG: ~3-5s per query
- Hybrid RAG: ~4-6s per query

**Optimization Strategies**:
- Batch embedding generation
- Connection pooling
- Result caching
- Parallel execution
- Async I/O

## Testing Strategy

```python
# Unit tests
pytest tests/test_rag_variants/

# Integration tests
pytest tests/ -m integration

# Coverage
pytest --cov=src --cov-report=html
```

## Monitoring & Metrics

**Tracked Metrics**:
- Query latency per variant
- Retrieval accuracy
- LLM token usage
- Database query performance
- Cache hit rates

**Output**:
- JSON results with metadata
- Statistical analysis reports
- Visualization plots
- Performance benchmarks

