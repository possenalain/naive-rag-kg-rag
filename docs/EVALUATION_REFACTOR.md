# Evaluation Pipeline Refactor

## Overview
The evaluation pipeline has been refactored to use JSON files for benchmark datasets and save results locally instead of using database storage.

## Key Changes

### 1. Configuration Updates
**File: `config/settings.py`**
- Changed default benchmark from `hotpotqa` to `factual_questions`
- Added `dataset_path` field for explicit benchmark file paths
- Added `datasets_dir` field (default: `./benchmarks/datasets`)
- The benchmark parameter now refers to the JSON filename without extension

### 2. Evaluation Orchestrator Refactor
**File: `src/evaluation/orchestrator.py`**
- **Removed database dependency** for loading questions and storing results
- Added `_load_questions_from_json()` method to load from JSON files
- Added `_save_results()` method to save results as local JSON files
- Results are saved with format: `eval_{timestamp}_{eval_id}_{benchmark}.json`
- Each evaluation gets a unique ID with timestamp
- Detailed results include all questions, answers, scores, and explanations

### 3. CLI Updates
**File: `cli.py`**
- Added `--dataset-path` option for explicit benchmark file paths
- Changed default dataset from `hotpotqa` to `factual_questions`
- Updated `status` command to show local evaluation files instead of database records

### 4. Database Schema Updates
**File: `sql/schema.sql`**
- Marked evaluation tables as **OPTIONAL**
- Added comments explaining the new JSON-based approach
- Tables remain for backwards compatibility but are not used by default

## Usage

### Running Evaluation with Default Dataset
```bash
uv run python cli.py evaluate
```
This loads `benchmarks/datasets/factual_questions.json` by default.

### Running Evaluation with Different Dataset
```bash
uv run python cli.py evaluate --dataset analytical_questions
```
This loads `benchmarks/datasets/analytical_questions.json`.

### Running Evaluation with Explicit Path
```bash
uv run python cli.py evaluate --dataset-path /path/to/custom/benchmark.json
```

### Limiting Number of Questions
```bash
uv run python cli.py evaluate --num-questions 10
```

### Custom Output Directory
```bash
uv run python cli.py evaluate --output-dir ./my_results
```

## Benchmark JSON Format

Benchmark files should follow this structure:

```json
{
  "dataset_name": "factual_questions",
  "description": "Factual single-hop questions",
  "question_type": "factual",
  "questions": [
    {
      "question_id": "fact_001",
      "question_text": "How much funding did OpenAI raise?",
      "ground_truth": "OpenAI raised $6.6 billion.",
      "source_documents": ["doc1_openai_funding.md"],
      "difficulty": "easy",
      "metadata": {
        "topic": "funding",
        "entities": ["OpenAI"],
        "answer_type": "amount"
      }
    }
  ]
}
```

## Results Output Format

Results are saved as JSON files in `benchmarks/results/` with this structure:

```json
{
  "evaluation_id": "20260110_143052_a1b2c3d4",
  "dataset_name": "factual_questions",
  "dataset_path": null,
  "num_questions": 50,
  "timestamp": "2026-01-10T14:30:52.123456",
  "summary": {
    "naive_rag": {
      "num_questions": 50,
      "avg_latency_ms": 1250.5,
      "avg_scores": {
        "correctness": 7.8,
        "completeness": 8.2,
        "relevance": 8.5,
        "faithfulness": 9.0,
        "clarity": 8.1
      }
    },
    "kg_rag": { /* ... */ },
    "hybrid_rag": { /* ... */ }
  },
  "detailed_results": {
    "naive_rag": [
      {
        "question_id": "fact_001",
        "question_text": "How much funding did OpenAI raise?",
        "ground_truth": "OpenAI raised $6.6 billion.",
        "generated_answer": "According to the documents...",
        "retrieved_chunks": [...],
        "latency_ms": 1234,
        "variant": "naive",
        "scores": {
          "correctness": 8.0,
          "completeness": 8.5,
          "relevance": 9.0,
          "faithfulness": 9.5,
          "clarity": 8.0,
          "explanations": { /* ... */ }
        }
      }
    ],
    "kg_rag": [ /* ... */ ],
    "hybrid_rag": [ /* ... */ ]
  }
}
```

## Benefits

1. **Simpler Setup**: No need to load benchmark data into database
2. **Version Control**: Benchmark datasets can be version controlled
3. **Portability**: Results are self-contained JSON files
4. **Easier Sharing**: Share benchmark datasets and results easily
5. **Reproducibility**: Results include full context (questions, answers, scores)
6. **No Database Bloat**: Evaluation data doesn't fill up database

## Migration Notes

- Existing database evaluation tables are kept for backwards compatibility
- Old evaluation results in database remain accessible
- New evaluations will use the JSON-based approach
- To use old approach, you would need to implement custom database loading

## Files Modified

- `config/settings.py` - Updated BenchmarkSettings
- `src/evaluation/orchestrator.py` - Refactored to use JSON files
- `cli.py` - Updated evaluate command and status command
- `sql/schema.sql` - Marked evaluation tables as optional
- `docs/EVALUATION_REFACTOR.md` - This documentation

## Next Steps

1. Run evaluation to test: `uv run python cli.py evaluate --num-questions 5`
2. Check results in `benchmarks/results/`
3. Add more benchmark datasets in `benchmarks/datasets/`
4. Consider adding result analysis tools
