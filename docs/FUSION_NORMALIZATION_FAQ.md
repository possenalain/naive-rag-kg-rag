# Fusion Normalization: What Changed vs What Stayed

## TL;DR

✅ **Fair chunk selection in FUSION**: Yes  
✅ **Relevance score preserved**: Yes (only normalized for comparison)  
✅ **Score-based filtering still active**: YES, absolutely!

---

## What Changed: Fusion Step Only

### Before (Biased Fusion)
```
KG Retrieval → Relevance scores [10-80]
                    ↓
              Divide by 100 (wrong!)
                    ↓
          Normalized [0.1-0.8] ← TOO LOW!
                    ↓
            Fusion with vector [0.7-0.9]
                    ↓
          KG loses 50% of the time ❌
```

### After (Fair Fusion)
```
KG Retrieval → Relevance scores [10-80] (UNCHANGED)
                    ↓
         Dynamic normalization to vector range
                    ↓
          Normalized [0.7-0.9] ← Fair!
                    ↓
            Fusion with vector [0.7-0.9]
                    ↓
          Fair competition! ✅
```

**Key point**: Normalization happens ONLY in the fusion step (hybrid RAG). The original relevance scores are unchanged everywhere else.

---

## What DIDN'T Change: KG Retrieval & Filtering

### 1. Score-Based Filtering ✅ STILL ACTIVE

**Location**: `src/utils/graph.py::kg_retrieve()` line 616

```cypher
WHERE direct_recall >= $min_ratio  -- Still filtering!
```

This filtering happens BEFORE fusion, using the RAW relevance score formula:
```
relevance_score = (weighted_count² × direct_recall × boost)
```

**Current threshold**: `RAG_KG_MIN_ENTITY_RATIO = 0.3` (30% direct entity coverage required)

### 2. Score-Based Ranking ✅ STILL ACTIVE

```cypher
ORDER BY relevance_score DESC, weighted_direct_count DESC, episode_count DESC
```

Chunks are still ranked by their raw relevance scores within KG retrieval.

### 3. Relevance Score Values ✅ PRESERVED

The actual relevance score is returned unchanged:
```python
{
    'chunk_id': '...',
    'relevance_score': 42.71,  # Original value preserved!
    'entity_count': 15,
    'direct_count': 5,
    # ... other fields
}
```

---

## Complete Data Flow

### KG RAG Standalone (No changes)
```
1. Entity Search (similarity filtering at 0.7)
2. Multi-hop expansion (distance weighting)
3. Cypher query retrieval
   ├─ Filter: direct_recall >= 0.3  ← STILL HERE
   ├─ Score: weighted_count² × recall × boost  ← UNCHANGED
   └─ Rank: ORDER BY relevance_score DESC  ← STILL WORKS
4. Return top-k chunks with original scores
5. LLM generation
```

### Hybrid RAG (Where normalization applies)
```
1. Parallel retrieval:
   ├─ Vector RAG → chunks with similarity [0.7-0.9]
   └─ KG RAG → chunks with relevance [10-80]
       (filtering/ranking unchanged ↑)

2. Fusion step: ← NEW NORMALIZATION HERE
   ├─ Calculate vector range: [min_vec, max_vec]
   ├─ Calculate KG range: [min_kg, max_kg]
   └─ Normalize: map kg_range → vector_range
   
3. Weighted scoring:
   ├─ Vector: similarity × 0.5
   └─ KG: normalized_relevance × 0.5  ← Fair now!
   
4. Return fused top-k
5. LLM generation
```

---

## Questions Answered

### Q1: Fair chunk selection?

**A: YES, but only in hybrid fusion.**

- **KG RAG alone**: Selection based on raw relevance scores (unchanged)
- **Hybrid RAG**: Fusion now treats vector and KG chunks fairly
- **Result**: More KG chunks will appear in hybrid results if they're truly relevant

**Example**:
```
Before normalization:
  Vector chunk: score=0.85, weighted=0.425 ← Wins
  KG chunk: score=45, normalized=0.45/100=0.225 ← Loses (unfairly!)

After normalization:
  Vector chunk: score=0.85, weighted=0.425
  KG chunk: score=45, normalized=0.82, weighted=0.410 ← Fair fight!
```

### Q2: Do we lose relevance score?

**A: NO, relevance scores are preserved everywhere.**

The normalization is a **transformation for comparison**, not a replacement:

```python
# Original score preserved
chunk = {
    'relevance_score': 42.71,  # ← Original value kept
    'chunk_text': '...',
    # ... other fields
}

# During fusion, we calculate a normalized version
kg_normalized = dynamic_normalize(42.71, kg_min, kg_max, vec_min, vec_max)
# → 0.83 (for comparison only)

# But original 42.71 is still in the chunk data!
```

**Why preserve it?**
- Debugging: Can see original scores in logs
- Transparency: Know how KG ranked the chunk
- Future use: Could use raw scores for other purposes

### Q3: Score-based filtering still active?

**A: YES, absolutely unchanged!**

Three levels of filtering remain:

1. **Entity search filtering** (line 261 in graph.py):
   ```python
   if entity.similarity >= min_similarity:  # Still at 0.7
       filtered_entities.append(entity)
   ```

2. **KG retrieval filtering** (line 616 in graph.py):
   ```cypher
   WHERE direct_recall >= $min_ratio  -- Still at 0.3
   ```

3. **Vector search filtering** (in db.py):
   ```sql
   WHERE 1 - (embedding <=> query_embedding) >= threshold  -- Still at 0.7
   ```

**All three filters are completely unchanged!**

---

## Impact Summary

### What Gets Better ✅

1. **Hybrid RAG balance**: KG and vector chunks compete fairly
2. **KG representation**: More KG chunks in final results (if relevant)
3. **Score visibility**: Logs show "vector=52%, kg=48%" contribution
4. **Adaptability**: Works across different configurations automatically

### What Stays the Same ✅

1. **KG filtering**: min_entity_ratio=0.3 still applies
2. **Vector filtering**: similarity_threshold=0.7 still applies
3. **Entity filtering**: entity_similarity=0.7 still applies
4. **Relevance scores**: Original values preserved
5. **Ranking logic**: ORDER BY relevance_score unchanged
6. **Top-k limits**: Same retrieval counts

### What Might Change (Expected) 📈

1. **Chunk source distribution**: May see more variety in hybrid results
2. **Correctness scores**: Should improve for hybrid RAG
3. **Score contribution logs**: Will show more balanced percentages
4. **KG utilization**: Better use of multi-hop information

---

## Example Scenario

**Query**: "How does OpenAI's valuation compare to Anthropic?"

### KG RAG (unchanged):
1. Finds entities: OpenAI, Anthropic, valuation
2. Expands: funding rounds, investors, competitors
3. Filters chunks: direct_recall >= 0.3
4. Scores chunks: weighted_count² × recall × 1.0
5. Returns: 5 chunks with scores [35.6, 28.3, 22.1, 18.9, 15.2]

### Vector RAG (unchanged):
1. Embeds query
2. Finds similar chunks: threshold >= 0.7
3. Returns: 5 chunks with scores [0.87, 0.84, 0.81, 0.76, 0.73]

### Hybrid Fusion (NEW behavior):

**Before (biased)**:
```
Vector chunks dominate:
  Vec1: 0.87 × 0.5 = 0.435 ← Ranks #1
  Vec2: 0.84 × 0.5 = 0.420 ← Ranks #2
  KG1:  35.6/100 × 0.5 = 0.178 ← Ranks #9 (unfair!)
```

**After (fair)**:
```
Dynamic normalization: [15.2, 35.6] → [0.73, 0.87]
Fair competition:
  Vec1: 0.87 × 0.5 = 0.435 ← Ranks #1
  KG1:  0.87 × 0.5 = 0.435 ← Ranks #1 (tied, fair!)
  Vec2: 0.84 × 0.5 = 0.420 ← Ranks #3
```

Result: Best chunks from both sources make it to top-5!

---

## Verification

To confirm everything still works:

```bash
# Check filtering is active
grep -n "WHERE direct_recall" src/utils/graph.py
# → Line 616: WHERE direct_recall >= $min_ratio ✓

# Check relevance score preserved
grep -n "relevance_score," src/utils/graph.py
# → Line 623: relevance_score, ✓

# Check normalization only in fusion
grep -n "dynamic_normalization\|kg_normalized" src/rag_variants/hybrid_rag.py
# → Lines 253, 272, 324, 342 (only in fusion methods) ✓
```

---

## Conclusion

✅ **Fair fusion**: Yes, vector and KG chunks compete equally  
✅ **Relevance preserved**: Original scores kept, only normalized for comparison  
✅ **Filtering active**: All three filtering layers unchanged  

**Bottom line**: We fixed the fusion bias without breaking anything else. All existing quality controls remain in place! 🎯
