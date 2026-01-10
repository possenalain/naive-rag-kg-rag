# Analysis System - Quick Reference

## 🚀 Quick Start

```bash
# Generate complete analysis
python cli.py analyze benchmarks/results/eval_*.json

# Custom output directory
python cli.py analyze benchmarks/results/eval_*.json --output-dir ./my_analysis

# Show plots interactively
python cli.py analyze benchmarks/results/eval_*.json --show-plots

# Export as PDF
python cli.py analyze benchmarks/results/eval_*.json --format pdf
```

## 📊 Outputs Generated

```
benchmarks/results/
├── analysis_report.txt              # Human-readable summary
├── detailed_results.csv             # All data points
├── summary_statistics.csv           # Aggregated stats
├── method_comparison.csv            # Side-by-side comparison
└── figures/
    ├── score_comparison.png         # Quality metrics
    ├── latency_comparison.png       # Performance
    ├── chunk_distribution.png       # Retrieval patterns
    ├── comprehensive_dashboard.png  # All-in-one view
    └── question_heatmap.png         # Per-question breakdown
```

## 🔍 What Each Visualization Shows

| Visualization | Purpose | Key Insights |
|--------------|---------|--------------|
| **Score Comparison** | Compare quality across 6 metrics | Which method scores highest? |
| **Latency Comparison** | Performance + distribution | Which is fastest? How consistent? |
| **Chunk Distribution** | Retrieval patterns | How many chunks per method? |
| **Comprehensive Dashboard** | All metrics in one view | Overall system behavior |
| **Question Heatmap** | Per-question breakdown | Which questions are challenging? |

## 📈 Key Metrics

| Metric | Scale | Meaning |
|--------|-------|---------|
| **Correctness** | 1-5 | Factual accuracy |
| **Completeness** | 1-5 | Addresses all parts of question |
| **Relevance** | 1-5 | On-topic, focused |
| **Faithfulness** | 1-5 | Grounded in retrieved context |
| **Clarity** | 1-5 | Well-written, understandable |
| **Latency** | milliseconds | Response time |
| **Chunks** | count | Documents retrieved |

## 🐍 Python API

```python
from src.analysis.metrics import *
from src.analysis.visualizations import *

# Load results
results = load_evaluation_results('results.json')
df = extract_detailed_results_to_dataframe(results)

# Analysis
summary = calculate_summary_stats(df)
comparison = compare_methods(results)
per_question = calculate_per_question_metrics(df)

# Visualizations
plot_score_comparison(df, 'scores.png')
plot_comprehensive_comparison(df, 'dashboard.png')

# Export
export_to_csv(df, 'output.csv')
report = generate_text_report(results)
```

## 📓 Jupyter Notebook

```bash
# Launch Jupyter
jupyter lab

# Open notebook
notebooks/analysis_tutorial.ipynb

# Run all cells to:
# - Load results
# - Generate visualizations
# - Create custom analysis
# - Export to CSV
```

## 🎯 Common Workflows

### Compare Methods
```bash
python cli.py analyze benchmarks/results/eval_latest.json
# View: method_comparison.csv
```

### Find Best Performer
```python
comparison = compare_methods(results)
best = comparison.iloc[0]
print(f"{best['Method']} - Score: {best['Overall Score']}")
```

### Latency vs Quality Trade-off
```python
import matplotlib.pyplot as plt

for method in df['method'].unique():
    data = df[df['method'] == method]
    plt.scatter(data['latency_ms'], data['avg_score'], label=method)

plt.xlabel('Latency (ms)')
plt.ylabel('Score')
plt.legend()
plt.show()
```

### Export for Excel
```python
with pd.ExcelWriter('analysis.xlsx') as writer:
    df.to_excel(writer, sheet_name='Detailed')
    summary.to_excel(writer, sheet_name='Summary')
```

## 🛠️ CLI Options

```
Usage: python cli.py analyze RESULT_FILES... [OPTIONS]

Arguments:
  RESULT_FILES...  One or more evaluation result JSON files

Options:
  --output-dir PATH       Output directory (default: benchmarks/results)
  --show-plots           Display plots interactively
  --format [png|pdf|svg] Figure format (default: png)
  --help                 Show this message
```

## 📚 Documentation

- **[ANALYSIS_GUIDE.md](ANALYSIS_GUIDE.md)** - Complete guide with examples
- **[ANALYSIS_SYSTEM_SUMMARY.md](ANALYSIS_SYSTEM_SUMMARY.md)** - Implementation details
- **[notebooks/analysis_tutorial.ipynb](notebooks/analysis_tutorial.ipynb)** - Interactive tutorial

## ⚡ Performance

- Load 100 results: ~0.5 seconds
- Generate all figures: ~3 seconds  
- Export CSVs: ~0.1 seconds
- **Total: < 5 seconds** ⚡

## ✅ No LLM Required

Pure data analysis with:
- pandas (DataFrames)
- numpy (statistics)
- matplotlib (plotting)
- seaborn (visualizations)

**No API calls, no costs, instant results!**

## 🎨 Customization

### Change Figure Colors
```python
# Edit src/analysis/visualizations.py
colors = ['#3498db', '#e74c3c', '#2ecc71']  # Blue, Red, Green
```

### Add Custom Metric
```python
def calculate_speed_efficiency(df):
    return df.groupby('method').apply(
        lambda x: x['avg_score'].mean() / x['latency_ms'].mean() * 1000
    )
```

### Filter by Question Type
```python
factual = df[df['question_id'].str.contains('fact')]
multihop = df[df['question_id'].str.contains('multi')]
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No result files | Run `python cli.py evaluate` first |
| Module not found | Run `uv sync` or `pip install -e .` |
| Figures not displaying | Add `%matplotlib inline` in Jupyter |
| CSV encoding errors | Use `pd.read_csv(file, encoding='utf-8')` |

## 💡 Pro Tips

1. **Run multiple times** to reduce variance
2. **Test on multiple datasets** (factual, multihop, analytical)
3. **Version control results** (create v1.0, v2.0 directories)
4. **Document findings** (save reports with context)
5. **Batch analyze** (`eval_*.json` pattern matches all)

## 🎉 You're Ready!

```bash
# 1. Run evaluation
python cli.py evaluate --dataset factual

# 2. Analyze results
python cli.py analyze benchmarks/results/eval_*.json

# 3. Review outputs
ls benchmarks/results/figures/
```

That's it! 🚀

---

**Need help?** Check [ANALYSIS_GUIDE.md](ANALYSIS_GUIDE.md) for detailed examples and troubleshooting.
