# Graphiti Neo4j 5.18+ Compatibility Solution

## Problem Summary

Graphiti-core 0.25.3 uses deprecated `SET n:$(node.labels)` syntax in Neo4j queries, which is incompatible with Neo4j 5.18+. This causes entity creation to fail during knowledge graph ingestion.

## Solution: Runtime Monkey Patching

We've implemented a sustainable runtime patching solution that:
- ✅ Persists across virtual environment recreations
- ✅ Requires no manual editing of installed packages
- ✅ Is version controlled in the project
- ✅ Works even when Graphiti is updated

## Implementation

### 1. Patch Module (`src/utils/graphiti_patches.py`)

The patch module replaces buggy Graphiti query functions at runtime:

- **`patch_entity_node_save_query()`**: Fixes single entity save queries
- **`patch_entity_node_save_bulk_query()`**: Fixes bulk entity save queries
- **`apply_all_patches()`**: Applies all patches and updates module references

### 2. Import Order (`src/utils/graph.py`)

**CRITICAL**: Patches MUST be applied BEFORE importing Graphiti:

```python
# WRONG - patches won't work!
from graphiti_core import Graphiti
from src.utils.graphiti_patches import apply_all_patches
apply_all_patches()

# CORRECT - patches applied first!
from src.utils.graphiti_patches import apply_all_patches
apply_all_patches()
from graphiti_core import Graphiti
```

### 3. Why Both Patches Are Needed

1. **Module-level patch**: Updates `node_db_queries.get_entity_node_save_bulk_query`
2. **bulk_utils patch**: Updates the already-imported reference in `graphiti_core.utils.bulk_utils`

Python's import system creates local references, so we must patch BOTH locations.

## Technical Details

### Original Buggy Query

```cypher
UNWIND $nodes AS node
MERGE (n:Entity {uuid: node.uuid})
SET n:$(node.labels)  # ❌ Deprecated in Neo4j 5.23+, broken in 5.18+
SET n = node
...
```

### Patched Query

```cypher
UNWIND $nodes AS node
MERGE (n:Entity {uuid: node.uuid})
SET n = node
WITH n, node
CALL apoc.create.setLabels(n, node.labels) YIELD node AS labeled_node  # ✅ APOC dynamic labels
...
```

## Verification

Test that the solution works:

```powershell
# Clean environment test
Remove-Item -Recurse -Force .\.venv
uv sync --all-extras

# Test ingestion
echo y | uv run python cli.py reset
uv run python cli.py ingest ./big_tech_docs
```

Expected result: **2 KG Entities** created (no errors)

## Files Modified

1. **`src/utils/graphiti_patches.py`** (NEW) - 120 lines
   - Runtime patches for Graphiti queries
   
2. **`src/utils/graph.py`** (MODIFIED)
   - Moved patch application before Graphiti imports

## Maintenance Notes

- If Graphiti updates fix this issue, simply remove the `apply_all_patches()` call
- If Graphiti changes query function names/locations, update the patch module accordingly
- The patch approach is version-agnostic and should work with future Graphiti releases

## Root Cause

Graphiti uses string templates with `$(node.labels)` expecting Neo4j to interpolate it as a dynamic label assignment. This syntax was deprecated in Neo4j 5.23 and doesn't work correctly in Neo4j 5.18. The proper approach is using APOC's `apoc.create.setLabels()` procedure for dynamic label assignment.
