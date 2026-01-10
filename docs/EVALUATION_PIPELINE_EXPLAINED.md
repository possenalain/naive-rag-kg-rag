# Evaluation Pipeline: Complete Technical Breakdown

This document explains the end-to-end evaluation pipeline for the three RAG variants (Naive, Knowledge Graph, and Hybrid), detailing every step from loading a question to saving the final scores.

## Table of Contents
- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Step-by-Step Walkthrough](#step-by-step-walkthrough)
- [RAG Variant Comparison](#rag-variant-comparison)
- [Scoring Mechanism](#scoring-mechanism)
- [Results Storage](#results-storage)

---

## Overview

The evaluation system compares three RAG approaches on benchmark datasets:
1. **Naive RAG**: Pure vector similarity search (PostgreSQL + pgvector)
2. **Knowledge Graph RAG**: Graph-based entity search (Neo4j + Graphiti)
3. **Hybrid RAG**: Combines vector + graph search

Each variant retrieves context differently but uses the same LLM for generation and the same scoring system for evaluation.

---

## Pipeline Architecture

```
┌─────────────────┐
│  JSON Dataset   │
│ (Questions +    │
│ Ground Truth)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│           Evaluation Orchestrator                        │
│  (src/evaluation/orchestrator.py)                       │
└─────────────────────────────────────────────────────────┘
         │
         ├─────────────┬─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
    ┌────────┐   ┌─────────┐   ┌─────────┐   ┌────────┐
    │ Naive  │   │   KG    │   │ Hybrid  │   │  LLM   │
    │  RAG   │   │   RAG   │   │   RAG   │   │ Scorer │
    └────────┘   └─────────┘   └─────────┘   └────────┘
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  JSON Results  │
              │  (with scores) │
              └────────────────┘
```

---

## Step-by-Step Walkthrough

### Phase 1: Initialization

**File**: `src/evaluation/orchestrator.py` → `initialize()`

1. **Database Setup**
   ```python
   self.db = await get_db()
   ```
   - Initializes PostgreSQL connection pool
   - Verifies pgvector extension

2. **LLM Providers**
   ```python
   self.llm_provider = await get_llm()
   self.embedder = await get_embedder()
   ```
   - Sets up Gemini API clients (or other providers)
   - Embedder: `text-embedding-004` (768 dimensions)
   - Generator: `gemini-2.0-flash`

3. **RAG Variants Initialization**
   ```python
   self.naive_rag = NaiveRAG(self.db, self.embedder, self.llm_provider)
   self.kg_rag = KnowledgeGraphRAG(self.graph_manager, self.db, self.llm_provider)
   self.hybrid_rag = HybridRAG(self.naive_rag, self.kg_rag)
   ```

4. **Scorer Setup**
   ```python
   self.scorer = LLMScorer(self.llm_provider)
   ```

---

### Phase 2: Question Loading

**File**: `src/evaluation/orchestrator.py` → `_load_questions_from_json()`

**Input**: `benchmarks/datasets/factual_questions.json`

**Structure**:
```json
{
  "dataset_name": "big_tech_factual",
  "questions": [
    {
      "question_id": "fact_001",
      "question_text": "How much funding did OpenAI raise?",
      "ground_truth": "OpenAI raised $6.6 billion.",
      "source_documents": ["doc1_openai_funding.md"],
      "metadata": {...}
    }
  ]
}
```

**Process**:
1. Load JSON file
2. Extract first N questions (if `num_questions` specified)
3. Parse into `BenchmarkQuestion` objects
4. Return list of questions

---

### Phase 3: RAG Execution (Per Variant)

#### 3A. Naive RAG Flow

**File**: `src/rag_variants/naive_rag.py` → `retrieve()`

**Step 1: Embed Query**
```python
query_embedding = await self.embedder.embed(query)
# Result: List[float] with 768 dimensions
```

**Step 2: Vector Search**
```python
chunks = await self.db.vector_search(
    query_embedding=query_embedding,
    top_k=5,
    similarity_threshold=0.7
)
```

**Database Query** (`src/utils/db.py`):
```sql
WITH ranked_chunks AS (
    SELECT 
        c.chunk_id,
        c.document_id,
        c.chunk_text,
        1 - (c.embedding <=> $1::vector) as similarity_score
    FROM chunks c
)
SELECT rc.*, d.title, d.source_path
FROM ranked_chunks rc
JOIN documents d ON rc.document_id = d.document_id
WHERE rc.similarity_score >= $2  -- 0.7 threshold
ORDER BY rc.similarity_score DESC
LIMIT $3  -- 5 chunks
```

**Key Technical Detail**: 
- Uses CTE (Common Table Expression) to calculate similarity once
- Avoids PostgreSQL recalculating distance in WHERE clause
- `<=>` is pgvector's cosine distance operator
- Similarity = `1 - distance`

**Step 3: Generate Answer**
```python
answer = await self.llm_provider.generate(
    prompt=user_prompt,
    system_prompt=system_prompt,
    temperature=0.1
)
```

**Prompt Template**:
```
System: You are a helpful assistant that answers questions based on provided context.

User: Based on the following documents, answer the question.

Documents:
[Document 1]
{chunk_text_1}

[Document 2]
{chunk_text_2}

Question: {question_text}

Provide a clear, concise answer based only on the information in the documents.
```

**Output**:
```python
{
    "answer": "OpenAI raised $6.6 billion...",
    "chunks": [...],
    "latency_ms": 690.88
}
```

---

#### 3B. Knowledge Graph RAG Flow

**File**: `src/rag_variants/kg_rag.py` → `retrieve()`

**Step 1: Entity Search**
```python
entity_results = await self.graph_manager.search(
    query=query,
    num_results=10
)
```

**Graphiti Search** (`src/utils/graph.py`):
1. **Hybrid Search** (Graphiti uses both):
   - Full-text search on entity names/summaries
   - Semantic search on entity embeddings

2. **Cypher Query** (approximate):
```cypher
// Full-text search
CALL db.index.fulltext.queryNodes("node_name_and_summary", $query)
YIELD node, score

// Combined with embedding similarity
MATCH (node:Entity)
WHERE node.embedding IS NOT NULL
WITH node, vector.similarity.cosine(node.embedding, $query_embedding) as sim
WHERE sim > 0.5
RETURN node, sim
ORDER BY sim DESC
LIMIT 10
```

**Result**: List of entity UUIDs

**Step 2: Extract Entity UUIDs**
```python
entity_uuids = self.graph_manager._extract_entity_uuids(entity_results)
# Example: ['uuid-1', 'uuid-2', 'uuid-3', ...]
```

**Step 3: Retrieve Associated Chunks**
```python
chunks = await self.graph_manager._retrieve_chunks_from_entities(entity_uuids)
```

**Database Query**:
```sql
SELECT DISTINCT ON (c.chunk_id)
    c.chunk_id,
    c.chunk_text,
    c.document_id,
    c.chunk_index,
    c.metadata,
    d.title,
    d.source_path,
    em.relevance_score
FROM chunks c
JOIN entity_mentions em ON c.chunk_id = em.chunk_id
JOIN documents d ON c.document_id = d.document_id
WHERE em.entity_uuid = ANY($1)  -- Array of UUIDs
ORDER BY c.chunk_id, em.relevance_score DESC
```

**Key Difference**: 
- Retrieves chunks based on entity relationships, not vector similarity
- Captures chunks that mention related entities
- More effective for multi-hop reasoning

**Step 4: Generate Answer**
```python
answer = await self.llm_provider.generate(...)
# Same LLM call as Naive RAG
```

**Output**:
```python
{
    "answer": "OpenAI raised $6.6 billion...",
    "chunks": [...],
    "latency_ms": 952.12
}
```

---

#### 3C. Hybrid RAG Flow

**File**: `src/rag_variants/hybrid_rag.py` → `retrieve()`

**Step 1: Parallel Retrieval**
```python
# Execute both searches concurrently
vector_chunks, kg_chunks = await asyncio.gather(
    self.naive_rag.retrieve(query),
    self.kg_rag.retrieve(query)
)
```

**Step 2: Deduplication**
```python
seen_chunk_ids = set()
merged_chunks = []

# Prefer vector chunks first (often more relevant)
for chunk in vector_chunks:
    if chunk['chunk_id'] not in seen_chunk_ids:
        merged_chunks.append(chunk)
        seen_chunk_ids.add(chunk['chunk_id'])

# Add KG chunks that weren't found by vector search
for chunk in kg_chunks:
    if chunk['chunk_id'] not in seen_chunk_ids:
        merged_chunks.append(chunk)
        seen_chunk_ids.add(chunk['chunk_id'])
```

**Step 3: Generate Answer**
```python
answer = await self.llm_provider.generate(...)
# Same LLM call, but with merged chunks
```

**Output**:
```python
{
    "answer": "OpenAI raised $6.6 billion...",
    "chunks": [...],  # Merged from both sources
    "latency_ms": 1115.08
}
```

---

### Phase 4: Scoring

**File**: `src/evaluation/llm_scorer.py` → `score_answer()`

**Process**: LLM-as-Judge approach

**Scoring Dimensions**:
1. **Correctness** (1-5): Factual accuracy vs ground truth
2. **Completeness** (1-5): Does it fully answer the question?
3. **Relevance** (1-5): Stays on topic, no tangents
4. **Faithfulness** (1-5): Grounded in context, no hallucinations
5. **Clarity** (1-5): Well-structured, readable

**Prompt Template**:
```
You are an expert evaluator. Score the following answer on a scale of 1-5.

Question: {question_text}
Ground Truth: {ground_truth}
Generated Answer: {generated_answer}
Retrieved Context: {chunks}

Evaluate on these dimensions:
1. Correctness: How factually accurate is the answer?
2. Completeness: Does it fully address the question?
3. Relevance: Is it on-topic without tangents?
4. Faithfulness: Is it grounded in the provided context?
5. Clarity: Is it well-written and easy to understand?

Respond in JSON format:
{
  "correctness": 5,
  "completeness": 5,
  "relevance": 5,
  "faithfulness": 5,
  "clarity": 5,
  "explanations": {
    "correctness": "...",
    "completeness": "...",
    "relevance": "...",
    "faithfulness": "...",
    "clarity": "...",
    "overall": "..."
  }
}
```

**Batching**: Scores 5 answers at a time to optimize API calls

---

### Phase 5: Results Aggregation

**File**: `src/evaluation/orchestrator.py` → `evaluate()`

**Per-Question Results**:
```python
{
    "question_id": "fact_001",
    "question_text": "How much funding did OpenAI raise?",
    "ground_truth": "OpenAI raised $6.6 billion.",
    "generated_answer": "OpenAI raised $6.6 billion...",
    "retrieved_chunks": [...],
    "latency_ms": 690.88,
    "variant": "naive",
    "scores": {
        "correctness": 5,
        "completeness": 5,
        "relevance": 5,
        "faithfulness": 5,
        "clarity": 5,
        "explanations": {...}
    }
}
```

**Summary Statistics**:
```python
{
    "naive_rag": {
        "num_questions": 3,
        "avg_latency_ms": 690.88,
        "avg_scores": {
            "correctness": 5.0,
            "completeness": 5.0,
            "relevance": 5.0,
            "faithfulness": 5.0,
            "clarity": 5.0
        }
    },
    "kg_rag": {...},
    "hybrid_rag": {...}
}
```

---

### Phase 6: Results Storage

**File**: `src/evaluation/orchestrator.py` → `_save_results()`

**Filename Format**:
```
eval_{timestamp}_{uuid}_{dataset_name}.json

Example:
eval_20260110_075356_8834caf2_factual_questions.json
```

**Complete Structure**:
```json
{
  "evaluation_id": "20260110_075356_8834caf2",
  "dataset_name": "factual_questions",
  "num_questions": 3,
  "timestamp": "2026-01-10T07:53:56.738945",
  "summary": {
    "naive_rag": {...},
    "kg_rag": {...},
    "hybrid_rag": {...}
  },
  "detailed_results": {
    "naive_rag": [...],
    "kg_rag": [...],
    "hybrid_rag": [...]
  }
}
```

**Storage Location**: `benchmarks/results/`

---

## RAG Variant Comparison

| Aspect | Naive RAG | Knowledge Graph RAG | Hybrid RAG |
|--------|-----------|---------------------|------------|
| **Retrieval Method** | Vector cosine similarity | Graph entity search | Both combined |
| **Database** | PostgreSQL + pgvector | Neo4j + Graphiti | Both |
| **Embedding Use** | Query → vector → search | Query → entities → chunks | Both |
| **Chunk Selection** | Top-K by similarity | By entity relationships | Deduplicated union |
| **Best For** | Single-hop, factual | Multi-hop, relational | Comprehensive coverage |
| **Avg Latency** | ~690ms | ~950ms | ~1115ms |
| **Complexity** | Low | Medium | High |

---

## Technical Deep Dives

### Vector Search Optimization

**Problem**: Original query hung due to WHERE clause recalculation
```sql
-- ❌ SLOW: Recalculates distance for every row
WHERE (1 - (embedding <=> $1::vector)) >= 0.7
```

**Solution**: CTE calculates once
```sql
-- ✅ FAST: Calculate similarity once in CTE
WITH ranked_chunks AS (
    SELECT ..., 1 - (embedding <=> $1::vector) as similarity_score
    FROM chunks
)
SELECT * FROM ranked_chunks
WHERE similarity_score >= 0.7
```

### Embedding Format

PostgreSQL pgvector requires specific format:
```python
# ❌ Wrong: Python str() representation
embedding_str = str([0.1, 0.2, 0.3])  # "[0.1, 0.2, 0.3]"

# ✅ Correct: PostgreSQL vector format
embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'  # "[0.1,0.2,0.3]"
```

### Graph Entity Extraction

Graphiti creates entities during ingestion:
1. LLM extracts entities from text
2. Creates nodes in Neo4j
3. Links entities to chunks via `entity_mentions` table
4. Builds relationships between entities

Query time:
1. Search entities by name/embedding
2. Follow links to find associated chunks
3. Rank chunks by relevance score

---

## Performance Characteristics

### Naive RAG
- **Pros**: Fast, simple, predictable
- **Cons**: Misses semantic connections beyond text similarity
- **Use Case**: Direct factual lookups

### Knowledge Graph RAG
- **Pros**: Captures relationships, multi-hop reasoning
- **Cons**: Slower, requires graph maintenance
- **Use Case**: Complex queries about entity relationships

### Hybrid RAG
- **Pros**: Best of both worlds, high recall
- **Cons**: Highest latency, complexity
- **Use Case**: When you need comprehensive coverage

---

## Scoring Methodology

### Why LLM-as-Judge?

Traditional metrics (BLEU, ROUGE) don't capture semantic correctness:
```
Ground Truth: "OpenAI raised $6.6 billion"
Answer 1: "OpenAI secured $6.6B in funding"  # BLEU: Low, but semantically correct
Answer 2: "OpenAI raised $6.6 billion"        # BLEU: High, exact match
```

LLM scorer understands:
- Semantic equivalence ("$6.6B" = "$6.6 billion")
- Paraphrasing validity
- Factual accuracy beyond text matching
- Context grounding (faithfulness)

### Reliability

- Uses temperature=0.1 for consistency
- Requires JSON output for structured scoring
- Includes explanations for transparency
- Batch processing for efficiency

---

## CLI Commands

```bash
# Run evaluation on 10 questions
uv run python cli.py evaluate --num-questions 10

# Run on specific dataset
uv run python cli.py evaluate --dataset factual_questions

# Custom output directory
uv run python cli.py evaluate --output-dir ./my_results

# Check evaluation status
uv run python cli.py status
```

---

## Key Takeaways

1. **All variants use the same LLM** for generation and scoring
2. **Retrieval is the differentiator** - how chunks are selected
3. **Hybrid combines both approaches** for maximum coverage
4. **Vector search requires careful query optimization** (CTE pattern)
5. **LLM-as-Judge provides nuanced evaluation** beyond text matching
6. **Results are fully reproducible** - saved with timestamps and UUIDs

---

## Future Enhancements

Potential improvements to the evaluation pipeline:

1. **Reranking**: Add cross-encoder reranking after retrieval
2. **Adaptive Retrieval**: Adjust top_k and threshold per question
3. **Query Expansion**: Generate multiple query variations
4. **Human Evaluation**: Add human judgments for calibration
5. **Confidence Scores**: Include model confidence in scoring
6. **Cost Tracking**: Monitor API costs per evaluation
7. **Caching**: Cache embeddings and scores for faster reruns
