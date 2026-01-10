# Analysis & Visualization Guide

Complete guide to analyzing and visualizing RAG evaluation results.

---

## Overview

The analysis system provides comprehensive tools for comparing RAG method performance:

- **CLI Tool**: Generate reports, figures, and CSVs automatically
- **Python API**: Programmatic access to metrics and visualizations
- **Jupyter Notebook**: Interactive exploration and custom analysis

---

## Quick Start

### 1. CLI Analysis

Generate complete analysis from command line:

```bash
# Analyze single result file
python cli.py analyze benchmarks/results/eval_20260110_075356_8834caf2_factual_questions.json

# Analyze multiple files
python cli.py analyze benchmarks/results/eval_*.json

# Custom output directory
python cli.py analyze benchmarks/results/eval_*.json --output-dir ./my_analysis

# Show plots interactively
python cli.py analyze benchmarks/results/eval_*.json --show-plots

# Export as PDF instead of PNG
python cli.py analyze benchmarks/results/eval_*.json --format pdf
```

### 2. Jupyter Notebook

For interactive exploration:

```bash
# Launch Jupyter
jupyter lab

# Open: notebooks/analysis_tutorial.ipynb
```

### 3. Python API

Use in your own scripts:

```python
from src.analysis.metrics import load_evaluation_results, compare_methods
from src.analysis.visualizations import plot_comprehensive_comparison

# Load results
results = load_evaluation_results('benchmarks/results/eval_*.json')

# Generate comparison
comparison = compare_methods(results)
print(comparison)

# Plot
plot_comprehensive_comparison(results)
```

---

## Output Files

### Directory Structure

```
benchmarks/results/
├── eval_20260110_075356_8834caf2_factual_questions.json  # Raw results
├── analysis_report.txt                                     # Text summary
├── detailed_results.csv                                    # All data points
├── summary_statistics.csv                                  # Aggregated stats
├── method_comparison.csv                                   # Head-to-head comparison
└── figures/
    ├── score_comparison.png                                # Quality scores
    ├── latency_comparison.png                              # Performance
    ├── chunk_distribution.png                              # Retrieval patterns
    ├── comprehensive_dashboard.png                         # All-in-one view
    └── question_heatmap.png                                # Per-question breakdown
```

### CSV Files

#### `detailed_results.csv`

Complete dataset with every question/method combination:

```csv
method,question_id,question_text,latency_ms,num_chunks,correctness,completeness,relevance,faithfulness,clarity,avg_score
Naive Rag,fact_001,How much funding did OpenAI raise?,822.62,1,5,5,5,5,5,5.0
Kg Rag,fact_001,How much funding did OpenAI raise?,860.08,2,5,5,5,5,5,5.0
...
```

**Use cases:**
- Custom statistical analysis
- Filtering by question type
- Correlating metrics
- ML model training

#### `summary_statistics.csv`

Aggregated statistics per method:

```csv
method,latency_ms_mean,latency_ms_std,num_chunks_mean,correctness_mean,...
Naive Rag,690.88,119.61,1.0,5.0,...
Kg Rag,952.12,137.32,2.0,5.0,...
Hybrid Rag,1115.08,109.49,2.0,5.0,...
```

**Use cases:**
- Quick performance overview
- Standard deviation analysis
- Identifying outliers
- Variability assessment

#### `method_comparison.csv`

Side-by-side method comparison with rankings:

```csv
Rank,Method,Overall Score,Correctness,Completeness,Relevance,Faithfulness,Clarity,Avg Latency (ms)
1,Naive Rag,5.0,5.0,5.0,5.0,5.0,5.0,690.88
1,Kg Rag,5.0,5.0,5.0,5.0,5.0,5.0,952.12
1,Hybrid Rag,5.0,5.0,5.0,5.0,5.0,5.0,1115.08
```

**Use cases:**
- Executive summaries
- Method selection
- Documentation
- Presentations

---

## Visualizations

### 1. Score Comparison

![Score Comparison](figures/score_comparison_example.png)

**Shows:**
- All 5 quality metrics (correctness, completeness, relevance, faithfulness, clarity)
- Average overall score
- Bar charts for easy comparison

**Interpretation:**
- Higher is better (scale 1-5)
- Perfect scores = 5.0
- Consistent high scores = reliable method

### 2. Latency Comparison

![Latency Comparison](figures/latency_comparison_example.png)

**Shows:**
- Average latency per method (bar chart)
- Distribution of latencies (box plot)
- Outliers and variability

**Interpretation:**
- Lower is faster
- Box plot shows median (red line), quartiles, and outliers
- Narrow boxes = consistent performance

### 3. Chunk Distribution

![Chunk Distribution](figures/chunk_distribution_example.png)

**Shows:**
- Average chunks retrieved per method
- Per-question chunk counts

**Interpretation:**
- Naive RAG: typically 1-2 chunks
- KG/Hybrid RAG: 2-5 chunks (entity-based)
- More chunks ≠ better quality (depends on relevance)

### 4. Comprehensive Dashboard

![Dashboard](figures/comprehensive_dashboard_example.png)

**All-in-one view showing:**
- Overall scores (horizontal bars)
- Latency comparison
- Chunk counts
- Score breakdown radar chart
- Latency vs quality scatter
- Score distribution violin plots

**Use cases:**
- Executive presentations
- Quick system overview
- Trade-off analysis

### 5. Question Heatmap

![Heatmap](figures/heatmap_example.png)

**Shows:**
- Performance on each individual question
- Color-coded scores (red = low, green = high)

**Interpretation:**
- Identify which questions are challenging
- Compare method strengths/weaknesses
- Spot patterns in failure modes

---

## Metrics Explained

### Quality Scores (1-5)

All scored by LLM-as-Judge (see [EVALUATION_PIPELINE_EXPLAINED.md](EVALUATION_PIPELINE_EXPLAINED.md)):

#### Correctness
**Definition:** Factual accuracy of the answer

**Example:**
- Question: "How much funding did OpenAI raise?"
- Ground truth: "$6.6 billion"
- Generated: "$6.6 billion" → Score: 5
- Generated: "$6 billion" → Score: 4 (close but imprecise)
- Generated: "$1 billion" → Score: 1 (wrong)

#### Completeness
**Definition:** Does the answer address all parts of the question?

**Example:**
- Question: "Who led the funding round and how much did they commit?"
- Answer: "Thrive Capital led the round with $1.2 billion" → Score: 5
- Answer: "Thrive Capital led the round" → Score: 3 (missing amount)
- Answer: "$1.2 billion was committed" → Score: 3 (missing who)

#### Relevance
**Definition:** Is the answer on-topic and focused?

**Example:**
- Question: "What was OpenAI's valuation?"
- Answer: "$157 billion post-money valuation" → Score: 5
- Answer: "OpenAI raised $6.6B at $157B valuation" → Score: 4 (extra info)
- Answer: "OpenAI is an AI company with a $157B valuation..." → Score: 2 (too much context)

#### Faithfulness
**Definition:** Is the answer grounded in the retrieved context?

**Example:**
- Context: "OpenAI raised $6.6 billion"
- Answer: "OpenAI raised $6.6 billion" → Score: 5
- Answer: "OpenAI raised significant funding" → Score: 4 (vague but true)
- Answer: "OpenAI raised $10 billion" → Score: 1 (hallucination)

#### Clarity
**Definition:** Is the answer well-written and easy to understand?

**Example:**
- "OpenAI raised $6.6 billion" → Score: 5 (clear, concise)
- "The funding amount that OpenAI has raised is $6.6 billion" → Score: 4 (wordy)
- "OpenAI, the company, raised, in their funding round, $6.6B" → Score: 2 (confusing structure)

### Performance Metrics

#### Latency (ms)
**Definition:** Time from question submission to answer generation

**Components:**
1. Retrieval time (vector/graph search)
2. LLM generation time
3. Post-processing

**Typical values:**
- Naive RAG: 500-800 ms
- KG RAG: 800-1200 ms
- Hybrid RAG: 1000-1500 ms

#### Chunk Count
**Definition:** Number of document chunks retrieved

**Impact:**
- More chunks = more context for LLM
- More chunks = slower processing
- Optimal: 2-5 relevant chunks

---

## Analysis Workflows

### Workflow 1: Initial Evaluation

**Goal:** First-time analysis of new results

```bash
# 1. Run evaluation
python cli.py evaluate --dataset factual --variants naive kg hybrid

# 2. Analyze results
python cli.py analyze benchmarks/results/eval_*.json

# 3. Review outputs
ls benchmarks/results/figures/
cat benchmarks/results/analysis_report.txt
```

### Workflow 2: Comparing Multiple Runs

**Goal:** Compare results across different configurations

```bash
# Run multiple evaluations with different settings
python cli.py evaluate --dataset factual --variants naive
python cli.py evaluate --dataset multihop --variants naive
python cli.py evaluate --dataset analytical --variants naive

# Analyze all together
python cli.py analyze benchmarks/results/eval_*_naive_*.json --output-dir analysis/naive_comparison
```

### Workflow 3: Interactive Exploration

**Goal:** Deep dive into specific patterns

```python
# In Jupyter notebook
from src.analysis.metrics import *
import pandas as pd

# Load all results
results = [load_evaluation_results(f) for f in result_files]

# Custom analysis
df = pd.concat([extract_detailed_results_to_dataframe(r) for r in results])

# Filter by question type
factual = df[df['question_id'].str.contains('fact')]
multihop = df[df['question_id'].str.contains('multi')]

# Compare
print(factual.groupby('method')['avg_score'].mean())
print(multihop.groupby('method')['avg_score'].mean())
```

### Workflow 4: Statistical Testing

**Goal:** Determine if differences are significant

```python
from scipy.stats import ttest_ind

# Load data
df = extract_detailed_results_to_dataframe(results)

# Get scores for each method
naive_scores = df[df['method'] == 'Naive Rag']['avg_score']
kg_scores = df[df['method'] == 'Kg Rag']['avg_score']

# T-test
t_stat, p_value = ttest_ind(naive_scores, kg_scores)

if p_value < 0.05:
    print(f"Significant difference (p={p_value:.4f})")
else:
    print(f"No significant difference (p={p_value:.4f})")
```

---

## Python API Reference

### Metrics Module

```python
from src.analysis.metrics import *

# Load results
results = load_evaluation_results('path/to/results.json')

# Extract to DataFrame
df = extract_detailed_results_to_dataframe(results)

# Summary statistics
stats = calculate_summary_stats(df)

# Method comparison
comparison = compare_methods(results)

# Per-question metrics
per_question = calculate_per_question_metrics(df)

# Score differences
differences = calculate_score_differences(df)

# Export to CSV
export_to_csv(df, 'output.csv')

# Generate text report
report = generate_text_report(results)
```

### Visualizations Module

```python
from src.analysis.visualizations import *
import matplotlib.pyplot as plt

# Individual plots
plot_score_comparison(df, save_path='scores.png')
plot_latency_comparison(df, save_path='latency.png')
plot_chunk_count_distribution(df, save_path='chunks.png')
plot_comprehensive_comparison(df, save_path='dashboard.png')
plot_per_question_heatmap(df, save_path='heatmap.png')

# Save all figures at once
saved_paths = save_all_figures(df, output_dir='./figures')

# Display interactively
fig = plot_comprehensive_comparison(df)
plt.show()
```

---

## Best Practices

### 1. Multiple Evaluation Runs

**Why:** Reduce variance, ensure reproducibility

```bash
# Run 3 times
for i in {1..3}; do
  python cli.py evaluate --dataset factual --variants naive kg hybrid
done

# Analyze all
python cli.py analyze benchmarks/results/eval_*.json
```

### 2. Dataset Diversity

**Why:** Test generalization across question types

```bash
# Test on multiple datasets
python cli.py evaluate --dataset factual
python cli.py evaluate --dataset multihop
python cli.py evaluate --dataset analytical

# Compare performance across datasets
python cli.py analyze benchmarks/results/eval_*_factual_*.json
python cli.py analyze benchmarks/results/eval_*_multihop_*.json
```

### 3. Version Control Results

**Why:** Track improvements over time

```bash
# Create versioned results directory
mkdir -p benchmarks/results/v1.0
python cli.py evaluate --output-dir benchmarks/results/v1.0

# Later, compare versions
python cli.py analyze benchmarks/results/v1.0/eval_*.json --output-dir analysis/v1.0
python cli.py analyze benchmarks/results/v2.0/eval_*.json --output-dir analysis/v2.0
```

### 4. Document Findings

**Why:** Communicate insights to stakeholders

- Save `analysis_report.txt` with each evaluation
- Add README.md explaining context
- Include figures in presentations
- Export CSVs for further analysis

---

## Troubleshooting

### Issue: "No result files found"

**Solution:**
```bash
# Check results directory
ls benchmarks/results/

# Run evaluation first
python cli.py evaluate --dataset factual
```

### Issue: "Module not found: matplotlib"

**Solution:**
```bash
# Install dependencies
uv sync
# or
pip install -e .
```

### Issue: Figures not displaying in Jupyter

**Solution:**
```python
# Add magic command
%matplotlib inline

# Or use
%matplotlib widget  # For interactive plots
```

### Issue: CSV encoding errors

**Solution:**
```python
# Explicitly specify encoding
df = pd.read_csv('results.csv', encoding='utf-8')
```

---

## Examples

### Example 1: Finding Best Method

```python
from src.analysis.metrics import compare_methods, load_evaluation_results

results = load_evaluation_results('benchmarks/results/eval_latest.json')
comparison = compare_methods(results)

# Sort by overall score
best = comparison.sort_values('Overall Score', ascending=False).iloc[0]

print(f"Best method: {best['Method']}")
print(f"Score: {best['Overall Score']}")
print(f"Latency: {best['Avg Latency (ms)']} ms")
```

### Example 2: Latency vs Quality Trade-off

```python
from src.analysis.metrics import extract_detailed_results_to_dataframe
import matplotlib.pyplot as plt

df = extract_detailed_results_to_dataframe(results)

# Plot trade-off
plt.figure(figsize=(10, 6))
for method in df['method'].unique():
    method_data = df[df['method'] == method]
    plt.scatter(method_data['latency_ms'], method_data['avg_score'], 
               label=method, s=100, alpha=0.7)

plt.xlabel('Latency (ms)')
plt.ylabel('Average Score')
plt.title('Latency vs Quality Trade-off')
plt.legend()
plt.grid(alpha=0.3)
plt.show()
```

### Example 3: Export for Excel

```python
# Generate comprehensive Excel workbook
import pandas as pd

with pd.ExcelWriter('rag_analysis.xlsx') as writer:
    detailed_df.to_excel(writer, sheet_name='Detailed Results', index=False)
    summary_df.to_excel(writer, sheet_name='Summary Stats', index=False)
    comparison_df.to_excel(writer, sheet_name='Comparison', index=False)

print("✓ Exported to rag_analysis.xlsx")
```

---

## Next Steps

1. **Run your first analysis:**
   ```bash
   python cli.py analyze benchmarks/results/eval_*.json
   ```

2. **Explore in Jupyter:**
   ```bash
   jupyter lab notebooks/analysis_tutorial.ipynb
   ```

3. **Read related docs:**
   - [EVALUATION_PIPELINE_EXPLAINED.md](EVALUATION_PIPELINE_EXPLAINED.md) - How evaluation works
   - [EMBEDDINGS_AND_KG_EXPLAINED.md](EMBEDDINGS_AND_KG_EXPLAINED.md) - How KG RAG works
   - [QUICKSTART.md](QUICKSTART.md) - Getting started guide

4. **Experiment:**
   - Try different datasets
   - Modify visualization colors/styles
   - Create custom metrics
   - Build your own analysis scripts

---

## Summary

The analysis system provides:

✅ **Automated reports** - CLI tool generates everything with one command  
✅ **Rich visualizations** - 5 figure types covering all metrics  
✅ **Structured data** - CSV exports for further analysis  
✅ **Interactive exploration** - Jupyter notebook for deep dives  
✅ **Python API** - Integrate into your own workflows  

**No LLM required** - Pure data analysis with pandas and matplotlib!
