# Full-Text Search Deep Dive: How Neo4j Handles Long Queries

## The Question

**"What if my query is long and has lots of entities? How does it know what to match against what?"**

Let me show you exactly how full-text search works in Neo4j/Graphiti, especially with complex queries.

---

## Full-Text Search: The Basics

### What is Full-Text Search?

Full-text search uses **Apache Lucene** (the same technology behind Elasticsearch). It's not just simple pattern matching - it's sophisticated text analysis that:

1. **Tokenizes** the query into words
2. **Normalizes** text (lowercase, stemming)
3. **Indexes** entity names and summaries for fast lookup
4. **Ranks** results by relevance (BM25 algorithm)

---

## Step-by-Step: From Query to Results

### Example Query

```
Query: "How much funding did OpenAI raise in their latest round with Thrive Capital and Microsoft?"
```

This is a **long query with multiple entities**: OpenAI, Thrive Capital, Microsoft

---

### Step 1: Query Sanitization

**File**: `graphiti_core/helpers.py` → `lucene_sanitize()`

```python
def lucene_sanitize(query: str) -> str:
    # Escape special Lucene characters
    # + - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
    
    # Original: "How much funding did OpenAI raise?"
    # After: "How much funding did OpenAI raise\?"
    
    escape_map = str.maketrans({
        '+': r'\+',
        '-': r'\-',
        '&': r'\&',
        '|': r'\|',
        '!': r'\!',
        '(': r'\(',
        ')': r'\)',
        # ... more special characters
    })
    
    return query.translate(escape_map)
```

**Why?** Lucene has special operators (AND, OR, NOT, wildcards). We need to escape them so they're treated as literal text.

**Result:**
```
"How much funding did OpenAI raise in their latest round with Thrive Capital and Microsoft\?"
```

---

### Step 2: Query Tokenization (by Lucene)

Lucene breaks the query into **tokens** (words):

```
Original: "How much funding did OpenAI raise in their latest round with Thrive Capital and Microsoft?"

Tokens:
1. "how"
2. "much"  
3. "funding"
4. "did"
5. "openai"          ← Entity!
6. "raise"
7. "in"
8. "their"
9. "latest"
10. "round"
11. "with"
12. "thrive"         ← Entity part 1
13. "capital"        ← Entity part 2
14. "and"
15. "microsoft"      ← Entity!
```

**Key Point:** Lucene treats multi-word entities like "Thrive Capital" as **separate tokens**!

---

### Step 3: Stop Words Removal (Automatic)

Lucene typically removes common words (stop words):

```
Removed: how, much, did, in, their, with, and

Remaining meaningful tokens:
- funding
- openai
- raise
- latest
- round
- thrive
- capital
- microsoft
```

---

### Step 4: Index Search

**What's in the Index?**

During ingestion, Neo4j created full-text indexes on entity names and summaries:

```cypher
CREATE FULLTEXT INDEX node_name_and_summary IF NOT EXISTS
FOR (n:Entity) ON EACH [n.name, n.summary, n.group_id]
```

**Index Contents:**

```
Entity: "OpenAI"
  Indexed tokens: ["openai"]
  Summary tokens: ["artificial", "intelligence", "research", "company", ...]

Entity: "Thrive Capital"  
  Indexed tokens: ["thrive", "capital"]
  Summary tokens: ["venture", "capital", "firm", "investment", ...]

Entity: "Microsoft"
  Indexed tokens: ["microsoft"]
  Summary tokens: ["technology", "corporation", "software", ...]

Entity: "$6.6 billion"
  Indexed tokens: ["6.6", "billion", "funding", "amount"]
  Summary tokens: ["money", "investment", "funding", "round", ...]
```

---

### Step 5: Matching Algorithm (BM25)

**BM25** (Best Match 25) is a ranking algorithm that scores each entity based on:

#### A. Term Frequency (TF)
How many query tokens match the entity?

```
Entity: "OpenAI"
  Query tokens that match: ["openai"] → 1 match
  TF score: 1

Entity: "Thrive Capital"
  Query tokens that match: ["thrive", "capital"] → 2 matches
  TF score: 2

Entity: "$6.6 billion"
  Query tokens that match: ["funding"] (from summary) → 1 match
  TF score: 1

Entity: "Microsoft"
  Query tokens that match: ["microsoft"] → 1 match
  TF score: 1
```

#### B. Inverse Document Frequency (IDF)
How rare/unique is the matched token?

```
Token: "openai" 
  Appears in: 1 entity (rare)
  IDF: HIGH → More important!

Token: "funding"
  Appears in: Many entities (common)
  IDF: LOW → Less important

Token: "capital"
  Appears in: Several entities (medium)
  IDF: MEDIUM
```

#### C. Field Length Normalization
Shorter entity names get boosted:

```
Entity: "OpenAI" (short name)
  Boost: HIGH

Entity: "Thrive Capital" (medium name)
  Boost: MEDIUM

Entity: "OpenAI's latest $6.6 billion funding round" (long name)
  Boost: LOW
```

#### D. Combined BM25 Score

```python
score = (TF * IDF * boost) / (TF + k * (1 - b + b * field_length / avg_field_length))

# Where:
# k = saturation parameter (typically 1.2)
# b = length normalization (typically 0.75)
```

**Result Rankings:**

```
1. Entity: "OpenAI" 
   Score: 8.5 (rare term, exact match, short name)

2. Entity: "Thrive Capital"
   Score: 7.2 (two matching tokens, medium rarity)

3. Entity: "Microsoft"
   Score: 6.8 (rare term, exact match)

4. Entity: "$6.6 billion"
   Score: 3.1 (common term "funding" in summary)

5. Entity: "funding round"
   Score: 2.5 (common terms)
```

---

### Step 6: Neo4j Full-Text Query Execution

**The actual Cypher query:**

```cypher
CALL db.index.fulltext.queryNodes(
    "node_name_and_summary",  -- Index name
    "funding openai raise latest round thrive capital microsoft"  -- Sanitized query
) YIELD node, score
WHERE node.group_id IN $group_ids  -- Optional filter
RETURN node
ORDER BY score DESC
LIMIT 10
```

**Key Behaviors:**

1. **OR Logic by Default**: Matches entities with ANY of the tokens
   - "OpenAI" matches → ✅ (has "openai")
   - "Thrive Capital" matches → ✅ (has "thrive" OR "capital")
   - "Amazon" doesn't match → ❌ (no matching tokens)

2. **Partial Matches Count**: 
   - "Thrive Capital" matches even if query only has "thrive"
   - "Microsoft Azure" matches if query has "microsoft"

3. **Fuzzy Matching** (optional):
   ```cypher
   CALL db.index.fulltext.queryNodes("index", "openai~1")
   -- Matches: "OpenAI", "openapi", "openid" (1 character difference)
   ```

---

## Handling Multiple Entities: How Disambiguation Works

### Scenario: "OpenAI and Microsoft funding"

**Query has TWO entities - how does it handle them?**

#### Method 1: OR Logic (Default)

```cypher
-- Finds entities matching "openai" OR "microsoft" OR "funding"
CALL db.index.fulltext.queryNodes("index", "openai microsoft funding")
```

**Results:**
```
1. Entity: "OpenAI" (matches "openai")
2. Entity: "Microsoft" (matches "microsoft")  
3. Entity: "$6.6 billion" (matches "funding" in summary)
4. Entity: "Microsoft Azure" (matches "microsoft")
5. Entity: "OpenAI ChatGPT" (matches "openai")
```

All entities that match **any** of the query tokens are returned!

#### Method 2: Proximity Boosting

If the index includes position information, entities where tokens appear **close together** get higher scores:

```
Entity: "OpenAI and Microsoft partnership"
  "openai" at position 0
  "microsoft" at position 2
  Distance: 2 tokens → HIGH BOOST

Entity: "OpenAI" (separate entity)
  "openai" at position 0
  "microsoft" not found
  Distance: N/A → LOWER SCORE
```

---

## Long Queries: Special Handling

### Query Length Limits

**From `search_utils.py`:**

```python
MAX_QUERY_LENGTH = 100  # tokens

def fulltext_query(query: str, group_ids: list[str] | None, driver: GraphDriver):
    lucene_query = lucene_sanitize(query)
    
    # If query is too long, return empty (fall back to semantic search)
    if len(lucene_query.split(' ')) + len(group_ids or '') >= MAX_QUERY_LENGTH:
        return ''  # This triggers semantic search instead!
```

**What happens with very long queries?**

```
Short Query (< 100 tokens):
  → Full-text search works normally

Long Query (>= 100 tokens):
  → Full-text search returns empty
  → System falls back to SEMANTIC SEARCH (embedding-based)
  → Uses query embedding to find similar entities
```

---

## Combining Full-Text + Semantic Search (Hybrid)

### Default Graphiti Behavior

**From `search.py`:**

```python
async def node_search(
    driver,
    cross_encoder,
    query,
    search_vector,  # Query embedding
    group_ids,
    config: NodeSearchConfig,
    ...
):
    # Step 1: Full-text search
    fulltext_nodes = await node_fulltext_search(driver, query, ...)
    
    # Step 2: Semantic search
    semantic_nodes = await node_similarity_search(driver, search_vector, ...)
    
    # Step 3: Combine with RRF (Reciprocal Rank Fusion)
    combined = rrf(fulltext_nodes, semantic_nodes)
    
    return combined
```

### RRF (Reciprocal Rank Fusion)

**How it merges results from both searches:**

```python
def rrf(fulltext_results, semantic_results, k=60):
    scores = {}
    
    # Full-text rankings
    for rank, entity in enumerate(fulltext_results):
        scores[entity] = 1 / (k + rank + 1)
    
    # Add semantic rankings
    for rank, entity in enumerate(semantic_results):
        scores[entity] += 1 / (k + rank + 1)
    
    # Sort by combined score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Example:**

```
Full-Text Results:
1. OpenAI (score: 8.5)
2. Thrive Capital (score: 7.2)
3. Microsoft (score: 6.8)

Semantic Results:
1. OpenAI (score: 0.92)
2. Microsoft (score: 0.88)
3. $6.6 billion (score: 0.82)

RRF Combined:
1. OpenAI (appears in both, rank 1 in both) → 1/61 + 1/61 = 0.0328
2. Microsoft (rank 3 in fulltext, rank 2 in semantic) → 1/63 + 1/62 = 0.0317
3. Thrive Capital (rank 2 in fulltext, not in semantic) → 1/62 = 0.0161
4. $6.6 billion (not in fulltext, rank 3 in semantic) → 1/63 = 0.0159
```

Entities appearing in **both** searches get the highest combined scores!

---

## Real Example: Your Actual Query

### Query

```
"How much funding did OpenAI raise in their latest round with Thrive Capital and Microsoft?"
```

### Processing

**1. Tokenization:**
```
Meaningful tokens: [funding, openai, raise, latest, round, thrive, capital, microsoft]
```

**2. Entity Matching:**

**Full-Text Search:**
```
CALL db.index.fulltext.queryNodes(
    "node_name_and_summary",
    "funding openai raise latest round thrive capital microsoft"
)

Results:
1. OpenAI (exact match on "openai") → BM25 score: 8.5
2. Thrive Capital (matches "thrive" AND "capital") → BM25 score: 7.2  
3. Microsoft (exact match on "microsoft") → BM25 score: 6.8
4. $6.6 billion (matches "funding" in summary) → BM25 score: 3.1
5. Funding round (matches "funding" and "round") → BM25 score: 2.5
```

**Semantic Search (parallel):**
```
Query embedding: [0.0064, 0.0189, ..., 0.0223]

Cosine similarity with entity embeddings:
1. OpenAI → 0.92 (very related)
2. Microsoft → 0.88 (related, investor)
3. $6.6 billion → 0.82 (funding amount)
4. Thrive Capital → 0.79 (related)
5. Venture funding → 0.75
```

**3. RRF Merge:**
```
Combined scores:
1. OpenAI: 0.0328 (top in both)
2. Microsoft: 0.0317 (high in both)
3. Thrive Capital: 0.0305 (high in both)
4. $6.6 billion: 0.0267 (medium in both)
```

**4. Graph Traversal:**
```cypher
-- With entity UUIDs: [openai-uuid, microsoft-uuid, thrive-uuid, 6.6b-uuid]

UNWIND $entity_ids as entity_uuid
MATCH (e:Entity {uuid: entity_uuid})
MATCH (e)<-[:MENTIONS]-(ep:Episodic)  -- Find episodes mentioning entities
MATCH (c:Chunk)-[:HAS_EPISODE]->(ep)  -- Find chunks
WITH DISTINCT c, COUNT(DISTINCT e) as entity_count
ORDER BY entity_count DESC
RETURN c

Results:
Chunk 35: mentions OpenAI, Thrive Capital, Microsoft, $6.6B → entity_count = 4 ✅ TOP!
Chunk 36: mentions Microsoft, Amazon → entity_count = 2
```

**Chunk 35 wins because it mentions the MOST entities from our query!**

---

## Key Insights

### 1. **Full-Text Search is Smart**
- Tokenizes queries automatically
- Removes stop words
- Uses BM25 ranking (considers term rarity, frequency, field length)
- Handles multi-word entities by matching individual tokens

### 2. **Multiple Entities = OR Logic**
- Finds entities matching ANY query token
- Higher scores for entities matching MORE tokens
- "OpenAI Microsoft" finds both entities separately

### 3. **Long Queries Fall Back to Semantic Search**
- Queries > 100 tokens skip full-text
- System automatically uses embedding-based search instead
- No manual configuration needed

### 4. **Hybrid is Best**
- Combines full-text (exact matches) + semantic (conceptual matches)
- RRF merging ensures entities strong in both get top scores
- Entities appearing in BOTH searches are most relevant

### 5. **Graph Traversal Disambiguates**
- After finding entities, traverse to chunks
- Chunks mentioning MULTIPLE query entities rank higher
- This naturally handles disambiguation

---

## Why This Works So Well

```
Query: "How much funding did OpenAI raise with Thrive Capital?"

Traditional Keyword Search:
  → Searches for exact strings "OpenAI", "Thrive Capital"
  → Misses if stored as "Open AI" or "Thrive"
  → Binary: match or no match

Full-Text Search (Lucene/BM25):
  → Tokenizes: ["openai", "thrive", "capital", "funding"]
  → Matches: "OpenAI" (openai), "Thrive Capital" (thrive + capital)
  → Ranks by relevance scores
  → Handles variations: "OpenAI's", "openai", "OPENAI"

Semantic Search (Embeddings):
  → Understands: "funding" = "investment" = "raised capital"
  → Finds conceptually related entities
  → Embeddings capture meaning, not just words

Hybrid (Full-Text + Semantic):
  → Gets precision of keyword matching
  → Gets recall of semantic understanding
  → Best of both worlds!

Graph Traversal:
  → "Which chunks mention BOTH OpenAI AND Thrive Capital?"
  → Natural disambiguation through entity co-occurrence
  → Chunks with more query entities = more relevant
```

---

## Summary

**"How does full-text search handle long queries with lots of entities?"**

1. **Tokenizes** the query into individual words
2. **Matches** entities that contain ANY of those words (OR logic)
3. **Ranks** by BM25 (rarity, frequency, length)
4. **Combines** with semantic search for conceptual matches
5. **Traverses** graph to find chunks mentioning multiple entities
6. **Returns** top chunks ranked by entity co-occurrence

The system is **smart enough** to:
- Handle multi-word entities ("Thrive Capital")
- Match entities even with word variations
- Rank entities with multiple matches higher
- Fall back to semantic search for very long queries
- Combine multiple search strategies for best results
- Use graph structure to find most relevant chunks

**No manual entity extraction needed at query time!** The full-text + semantic hybrid search handles it all automatically.
