# Embeddings and Knowledge Graph RAG: Technical Deep Dive

This document answers two critical questions:
1. **How are embeddings represented?** (Query and chunk vectors)
2. **How does KG RAG go from query to entities?** (No LLM needed!)

---

## Part 1: Understanding Embeddings

### Query Embeddings

**Short Answer**: A query is represented by a **single 768-dimensional vector**.

**How it works:**

```python
# User query
query = "How much funding did OpenAI raise?"

# Step 1: Call embedding API (Google text-embedding-004)
query_embedding = await embedder.embed(query)

# Result: A single vector (Python list of floats)
query_embedding = [0.0064, 0.0189, 0.0054, -0.0386, ..., 0.0223]  # 768 floats

# Type: List[float]
len(query_embedding)  # 768
type(query_embedding)  # <class 'list'>
```

**Key Points:**
- ✅ **ONE vector per query** (not a list of vectors)
- ✅ **768 dimensions** (specific to text-embedding-004 model)
- ✅ Each dimension is a float between -1 and 1
- ✅ The entire query is encoded into this single vector

**Why 768?**
Different embedding models produce different dimensions:
- `text-embedding-004` (Google): 768 dimensions
- `text-embedding-3-small` (OpenAI): 1536 dimensions
- `all-MiniLM-L6-v2` (Sentence Transformers): 384 dimensions

Our system uses Google's `text-embedding-004`, hence 768.

---

### Chunk Embeddings in Database

**Short Answer**: Each chunk is represented by a **single 768-dimensional vector** stored in PostgreSQL.

**How it's stored:**

```sql
-- Chunks table schema
CREATE TABLE chunks (
    chunk_id SERIAL PRIMARY KEY,
    document_id INTEGER,
    chunk_text TEXT,
    chunk_index INTEGER,
    embedding vector(768),  -- Single 768-dimensional vector
    metadata JSONB,
    created_at TIMESTAMP
);
```

**During Ingestion:**

```python
# Original document
doc = "OpenAI has closed one of the largest venture funding rounds..."

# Split into chunks (each ~500 words)
chunks = [
    "OpenAI has closed one of the largest venture funding rounds...",  # Chunk 1
    "The company's valuation now stands at $157 billion...",           # Chunk 2
    # ... more chunks
]

# For EACH chunk, generate ONE embedding
for chunk in chunks:
    # Generate single 768-dimensional vector for this chunk
    embedding = await embedder.embed(chunk)  # List[float] with 768 elements
    
    # Store in database
    await db.insert_chunk(
        chunk_text=chunk,
        embedding=embedding  # [0.023, -0.045, 0.091, ..., 0.018]
    )
```

**Key Points:**
- ✅ **ONE vector per chunk** (not multiple vectors)
- ✅ **768 dimensions** (same as query embeddings)
- ✅ Each chunk's entire text content is condensed into one vector
- ✅ Vector is stored in PostgreSQL's `vector` type (from pgvector extension)

---

### How Similarity Calculation Works

**The Math:**

Given:
- Query embedding: `Q = [q1, q2, q3, ..., q768]`
- Chunk embedding: `C = [c1, c2, c3, ..., c768]`

**Cosine Similarity:**

```
similarity = 1 - cosine_distance

cosine_distance = 1 - (Q · C) / (||Q|| × ||C||)

Where:
- Q · C = dot product = q1*c1 + q2*c2 + ... + q768*c768
- ||Q|| = magnitude of Q = sqrt(q1² + q2² + ... + q768²)
- ||C|| = magnitude of C = sqrt(c1² + c2² + ... + c768²)
```

**In PostgreSQL with pgvector:**

```sql
-- Cosine distance operator: <=>
SELECT 
    chunk_id,
    chunk_text,
    1 - (embedding <=> '[0.0064,0.0189,0.0054,...]'::vector) as similarity
FROM chunks
WHERE (1 - (embedding <=> '[0.0064,0.0189,0.0054,...]'::vector)) >= 0.7
ORDER BY embedding <=> '[0.0064,0.0189,0.0054,...]'::vector
LIMIT 5;
```

**Example Calculation:**

```
Query: "How much funding did OpenAI raise?"
Query Embedding: [0.0064, 0.0189, ..., 0.0223]  (768 floats)

Chunk 35: "OpenAI has closed one of the largest venture funding rounds..."
Chunk 35 Embedding: [0.0071, 0.0195, ..., 0.0241]  (768 floats)

Cosine Distance = 0.2077
Similarity = 1 - 0.2077 = 0.7923  ✅ Above 0.7 threshold!

Chunk 36: "Amazon Web Services announced a significant expansion..."
Chunk 36 Embedding: [0.0023, 0.0512, ..., 0.0089]  (768 floats)

Cosine Distance = 0.4188
Similarity = 1 - 0.4188 = 0.5812  ❌ Below 0.7 threshold, filtered out
```

**Key Points:**
- ✅ Compare **two vectors of the same dimension** (768 = 768)
- ✅ Result is a **single number** between 0 and 1
- ✅ Higher similarity = more semantically related
- ✅ Threshold of 0.7 means "70% similar"

---

### Visual Representation

```
Query: "How much funding did OpenAI raise?"
   │
   │  Embedding API
   ▼
[0.0064, 0.0189, 0.0054, -0.0386, ..., 0.0223]  ← Single 768-dimensional vector
   │
   │  Vector Search
   ▼
┌─────────────────────────────────────────────────┐
│  PostgreSQL Database                            │
│                                                 │
│  Chunk 35 (ID: 35)                             │
│  Text: "OpenAI has closed..."                  │
│  Embedding: [0.0071, 0.0195, ..., 0.0241]     │ ← 768 dimensions
│  Similarity: 0.7923 ✅                          │
│                                                 │
│  Chunk 36 (ID: 36)                             │
│  Text: "Amazon Web Services..."                │
│  Embedding: [0.0023, 0.0512, ..., 0.0089]     │ ← 768 dimensions
│  Similarity: 0.5812 ❌ (below threshold)        │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Part 2: Knowledge Graph RAG - Query to Entities

### The Big Question

**"How do we go from query to entities in KG RAG? Do we call an LLM to extract entities?"**

**Short Answer**: **NO LLM is called at query time!** Graphiti uses **hybrid search** (full-text + semantic) on pre-existing entities.

---

### How It Actually Works

#### Step 1: Query Submission

```python
# User query
query = "How much funding did OpenAI raise?"

# KG RAG calls Graphiti search
search_results = await graphiti.search(
    query=query,
    num_results=10
)
```

#### Step 2: Graphiti Hybrid Search (NO LLM!)

Graphiti performs **two searches simultaneously** and merges results:

**2A. Full-Text Search** (Fast, exact matching)

```cypher
// Neo4j full-text index search
CALL db.index.fulltext.queryNodes(
    "node_name_and_summary",  // Index on entity names and summaries
    "OpenAI funding"          // Query text
) YIELD node, score
RETURN node
ORDER BY score DESC
LIMIT 10
```

This finds entities whose **names or summaries** contain words like "OpenAI", "funding", etc.

**2B. Semantic Search** (Embeddings, similarity-based)

```cypher
// Find entities with similar embeddings
MATCH (e:Entity)
WHERE e.embedding IS NOT NULL
WITH e, 
     vector.similarity.cosine(
         e.embedding, 
         $query_embedding  // Pre-computed query embedding
     ) as similarity
WHERE similarity > 0.5
RETURN e, similarity
ORDER BY similarity DESC
LIMIT 10
```

This finds entities whose **embeddings** are semantically similar to the query.

**2C. Merge Results**

Graphiti combines both result sets, deduplicates, and ranks by relevance.

**Key Point**: The query embedding is generated (via Google API), but **no LLM is called to extract entities from the query text**. Instead, we search through entities that were **already extracted during ingestion**.

---

### What Happens During Ingestion (One-Time Setup)

**This is when entities are extracted (using LLM):**

```python
# During ingestion of a document
doc_text = "OpenAI has closed one of the largest venture funding rounds..."

# Graphiti calls LLM to extract entities
results = await graphiti.add_episode(
    name="doc1_chunk_0",
    content=doc_text,
    source_description="TechCrunch article about OpenAI funding"
)

# LLM extracts entities (this is where the LLM is used!)
# Results:
# - Entity: "OpenAI" (type: Organization, summary: "AI research company...")
# - Entity: "Thrive Capital" (type: Organization, summary: "Venture capital firm...")
# - Entity: "$6.6 billion" (type: Amount, summary: "Funding amount...")
# - Relationship: OpenAI -[RAISED]-> $6.6 billion
```

**These entities are now stored in Neo4j:**

```
Neo4j Graph Database:
┌─────────────────────┐
│ Entity: OpenAI      │
│ uuid: abc-123       │
│ name: "OpenAI"      │
│ embedding: [...]    │ ← 768-dimensional vector of "OpenAI"
│ summary: "AI..."    │
└─────────────────────┘
          │
          │ [RAISED]
          ▼
┌─────────────────────┐
│ Entity: $6.6B       │
│ uuid: def-456       │
│ name: "$6.6 billion"│
│ embedding: [...]    │
│ summary: "Amount..." │
└─────────────────────┘
```

---

### Query Time: No Entity Extraction!

**At query time (during evaluation):**

```python
# Query: "How much funding did OpenAI raise?"

# ❌ We DON'T do this:
# entities = await llm.extract_entities(query)  # NOPE!

# ✅ We DO this instead:
# Search for existing entities that match the query
search_results = await graphiti.search(query="How much funding did OpenAI raise?")

# Graphiti returns entities that were already in the graph:
# - Entity "OpenAI" (matched via full-text on name)
# - Entity "$6.6 billion" (matched via semantic similarity)
# - Entity "Thrive Capital" (matched via relationships)
```

**Why this is faster:**
- No LLM call needed at query time
- Full-text search is extremely fast (milliseconds)
- Semantic search uses pre-computed embeddings
- Only LLM call is for generating the final answer

---

### Complete KG RAG Flow

```
┌─────────────────────────────────────────────────────────┐
│ INGESTION TIME (One-time, uses LLM)                     │
├─────────────────────────────────────────────────────────┤
│ 1. Document: "OpenAI has closed..."                     │
│ 2. LLM extracts entities: OpenAI, Thrive Capital, $6.6B │
│ 3. Create entity nodes in Neo4j with embeddings         │
│ 4. Create relationships: OpenAI -[RAISED]-> $6.6B      │
│ 5. Link entities to chunks (episode nodes)              │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Entities stored in graph
                         ▼
┌─────────────────────────────────────────────────────────┐
│ QUERY TIME (Fast, no LLM for entity extraction)        │
├─────────────────────────────────────────────────────────┤
│ 1. Query: "How much funding did OpenAI raise?"         │
│ 2. Graphiti searches existing entities:                 │
│    - Full-text: "OpenAI", "funding" → finds entities   │
│    - Semantic: query embedding → similar entities       │
│ 3. Results: [OpenAI, $6.6B, Thrive Capital, ...]       │
│ 4. Get entity UUIDs: [abc-123, def-456, ghi-789]       │
│ 5. Query Neo4j for chunks mentioning these entities:   │
│    Chunk 35 mentions OpenAI and $6.6B ✅                │
│ 6. Return chunks to LLM for answer generation           │
│ 7. LLM generates: "OpenAI raised $6.6 billion..."      │
└─────────────────────────────────────────────────────────┘
```

---

### The Actual Neo4j Query

**After Graphiti returns entity UUIDs, we query Neo4j:**

```cypher
// Input: entity_ids = ['abc-123', 'def-456', 'ghi-789']

UNWIND $entity_ids as entity_uuid
MATCH (e:Entity {uuid: entity_uuid})              // Find entity
MATCH (e)<-[:MENTIONS]-(ep:Episodic)              // Find episodic nodes mentioning it
MATCH (c:Chunk)-[:HAS_EPISODE]->(ep)              // Find chunks linked to episodic
WITH DISTINCT c, COUNT(DISTINCT e) as entity_count  // Count how many entities per chunk
ORDER BY entity_count DESC                          // Rank by relevance
LIMIT $top_k                                        // Return top K chunks
RETURN c.chunk_id, c.chunk_text, entity_count as relevance_score
```

**Graph Traversal:**

```
Query: "How much funding did OpenAI raise?"
   │
   │ Graphiti Search (no LLM!)
   ▼
Entities Found: [OpenAI, $6.6B, Thrive Capital]
   │
   │ Neo4j Traversal
   ▼
┌──────────────────────────────────────────────────┐
│  Entity: OpenAI                                  │
│  uuid: abc-123                                   │
└────────────┬─────────────────────────────────────┘
             │
             │ [:MENTIONS]
             ▼
┌──────────────────────────────────────────────────┐
│  Episodic Node: "doc1_chunk_0"                   │
│  content: "OpenAI has closed..."                 │
└────────────┬─────────────────────────────────────┘
             │
             │ [:HAS_EPISODE]
             ▼
┌──────────────────────────────────────────────────┐
│  Chunk 35                                        │
│  chunk_text: "OpenAI has closed..."              │
│  relevance_score: 2 (mentions 2 entities)        │
└──────────────────────────────────────────────────┘
```

---

## Comparison: Naive RAG vs KG RAG

### Naive RAG

```
Query → Embedding → Vector Search → Chunks
  │         │              │            │
  │         │              │            └─ Ranked by vector similarity
  │         │              └─ Compare to all chunk embeddings
  │         └─ Single 768-dim vector
  └─ "How much funding did OpenAI raise?"
```

**Pros:**
- Simple, direct
- Fast (single vector comparison)
- No graph maintenance

**Cons:**
- Misses semantic connections
- Can't do multi-hop reasoning

---

### KG RAG

```
Query → Graphiti Search → Entity UUIDs → Neo4j Traversal → Chunks
  │           │                │               │              │
  │           │                │               │              └─ Ranked by entity_count
  │           │                │               └─ Follow graph relationships
  │           │                └─ ['abc-123', 'def-456', ...]
  │           └─ Full-text + Semantic search (no LLM!)
  └─ "How much funding did OpenAI raise?"
```

**Pros:**
- Captures entity relationships
- Multi-hop reasoning
- More context-aware

**Cons:**
- More complex
- Requires graph maintenance
- Slightly slower

---

## Key Takeaways

### Embeddings

1. ✅ **Query = ONE vector** (768 dimensions)
2. ✅ **Chunk = ONE vector** (768 dimensions)  
3. ✅ **Similarity = comparing two 768-dim vectors**
4. ✅ **Result = single number (0 to 1)**

### KG RAG Entity Search

1. ✅ **NO LLM at query time** for entity extraction
2. ✅ **Graphiti uses hybrid search** (full-text + semantic)
3. ✅ **Entities were extracted during ingestion** (one-time LLM call)
4. ✅ **Query time = search existing entities + graph traversal**
5. ✅ **LLM only used for final answer generation**

### Why This Matters

- **Naive RAG**: "Find chunks with similar words/concepts"
- **KG RAG**: "Find chunks about entities related to my query"
- **Hybrid RAG**: "Use both approaches for comprehensive coverage"

The beauty of KG RAG is that it leverages the **pre-built knowledge graph** created during ingestion, making query-time retrieval fast and relationship-aware without needing additional LLM calls for entity extraction!
