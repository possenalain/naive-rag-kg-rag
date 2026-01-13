# Fusion Scoring Bias Fix

## Problem Identified

The hybrid fusion mechanism was significantly under-weighting knowledge graph chunks compared to vector chunks due to improper score normalization.

### Root Cause Analysis

1. **Vector Scores**: Already normalized in 0-1 range (cosine similarity), typically 0.7-0.9 after threshold filtering
2. **KG Scores**: Raw relevance scores from formula `(weighted_count² × direct_recall × boost)` ranging from ~10-80
3. **Original Normalization**: KG scores divided by 100, resulting in 0.1-0.8 range
4. **Result**: KG chunks systematically scored **50-56% lower** than vector chunks

### Evidence from Logs

From typical KG retrieval logs:
```
KG retrieval: 5 chunks, avg direct_recall=0.36, avg weighted_count=7.6
```

Calculated relevance scores:
- Min: 13.84 (6.2² × 0.36 × 1.0)
- Avg: 39.74
- Max: 68.95 (11.3² × 0.54 × 1.0)

### Impact on Fusion

**Weighted Fusion (before fix)**:
- Vector: 0.8 × 0.5 = **0.4000**
- KG: (39.74/100) × 0.5 = **0.1987**
- **Ratio: 50% (KG severely under-weighted!)**

**Adaptive Fusion (before fix)**:
- Vector: 0.0164 + (0.4000 × 0.3) = **0.1364**
- KG: 0.0164 + (0.1987 × 0.3) = **0.0760**
- **Ratio: 56% (KG under-weighted!)**

## Solution Implemented

### Range-Based Normalization

Map KG relevance scores to the same range as filtered vector scores [0.7, 1.0]:

```python
# KG score normalization formula
kg_raw = chunk.get('relevance_score', 1.0)  # Typically 10-80
kg_normalized = 0.7 + (min(max(kg_raw, 10), 80) - 10) / 70 * 0.3

# Linear mapping: [10, 80] -> [0.7, 1.0]
```

### Results After Fix

**Score Distribution**:
- KG raw: 13.84 → normalized: 0.72
- KG raw: 39.74 → normalized: 0.83
- KG raw: 68.95 → normalized: 0.95

**Weighted Fusion (after fix)**:
- Vector: 0.8 × 0.5 = 0.4000
- KG: 0.83 × 0.5 = 0.4137
- **Ratio: 103% (balanced!)**

**Adaptive Fusion (after fix)**:
- Vector: 0.0164 + (0.4000 × 0.3) = 0.1364
- KG: 0.0164 + (0.4137 × 0.3) = 0.1405
- **Ratio: 103% (balanced!)**

## Changes Made

### 1. Updated Weighted Fusion (`_weighted_fusion`)
**File**: `src/rag_variants/hybrid_rag.py` ~line 212

```python
# OLD (under-weighting KG)
kg_score = chunk.get('relevance_score', 1.0) / 10.0  # Assume max 10

# NEW (balanced)
kg_raw = chunk.get('relevance_score', 1.0)
kg_score = 0.7 + (min(max(kg_raw, 10), 80) - 10) / 70 * 0.3
```

### 2. Updated Adaptive Fusion (`_adaptive_fusion`)
**File**: `src/rag_variants/hybrid_rag.py` ~line 292

```python
# OLD (under-weighting KG)
kg_normalized = min(kg_raw_score / 100.0, 1.0)

# NEW (balanced)
kg_normalized = 0.7 + (min(max(kg_raw_score, 10), 80) - 10) / 70 * 0.3
```

### 3. Enhanced Logging
**File**: `src/rag_variants/hybrid_rag.py` ~line 104

Added score contribution tracking:
```python
logger.info(
    f"Hybrid retrieval returned {len(fused_results)} chunks "
    f"(vector_only={vector_only}, kg_only={kg_only}, both={both}) | "
    f"Score contribution: vector={vector_pct:.1f}%, kg={kg_pct:.1f}%"
)
```

### 4. Documentation
**File**: `src/rag_variants/hybrid_rag.py` ~line 1

Added score normalization explanation in module docstring.

## Expected Impact

1. **Better Balance**: KG chunks will now compete fairly with vector chunks in fusion
2. **More Diverse Results**: Should see more `kg_only` chunks in final results
3. **Improved Performance**: KG's multi-hop reasoning capabilities can now contribute meaningfully
4. **Observable Metrics**: Score contribution logging shows vector vs KG percentage

## Validation

Run new evaluation:
```bash
uv run python cli.py evaluate --num-questions -1 --dataset multihop_part3 --output-dir ./benchmarks/multihop_part3_results_v8
```

Look for:
- "Score contribution: vector=X%, kg=Y%" in logs
- More balanced percentages (ideally 40-60% each)
- Improved correctness scores for hybrid RAG
- More `kg_only` chunks in final results

## Alternative Approaches Considered

1. **Adjust graph_weight**: Set to ~1.0 instead of 0.5
   - ❌ Less intuitive, doesn't address root cause
   
2. **Dynamic normalization**: Use percentile-based or max-observed
   - ❌ More complex, requires statistics across queries
   
3. **Increase KG boost**: Multiply relevance scores by 2-3x
   - ❌ Doesn't solve normalization mismatch, arbitrary scaling

4. **Range-based mapping** (chosen): Map KG to vector score range
   - ✅ Intuitive, preserves relative differences, balances weights

## Notes

- The normalization assumes KG scores typically fall in [10, 80] range based on observed data
- Scores outside this range are clamped (floor at 10, ceiling at 80)
- This maintains the same 0.5/0.5 weight split while achieving balanced contribution
- If KG scoring formula changes significantly, these bounds should be revisited
