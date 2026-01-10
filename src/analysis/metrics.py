"""Metrics calculation and data processing for RAG evaluation results."""

import json
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
import numpy as np


def load_evaluation_results(result_file: str | Path) -> Dict[str, Any]:
    """Load evaluation results from JSON file.
    
    Args:
        result_file: Path to evaluation results JSON file
        
    Returns:
        Dictionary containing evaluation results
    """
    with open(result_file, 'r') as f:
        return json.load(f)


def extract_detailed_results_to_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
    """Extract detailed results for all methods into a single DataFrame.
    
    Args:
        results: Loaded evaluation results dictionary
        
    Returns:
        DataFrame with columns: method, question_id, question_text, 
                                latency_ms, num_chunks, correctness, 
                                completeness, relevance, faithfulness, clarity
    """
    rows = []
    
    for method in ['naive_rag', 'kg_rag', 'hybrid_rag']:
        if method not in results.get('detailed_results', {}):
            continue
            
        for result in results['detailed_results'][method]:
            row = {
                'method': method.replace('_', ' ').title(),
                'question_id': result['question_id'],
                'question_text': result['question_text'],
                'latency_ms': result['latency_ms'],
                'num_chunks': len(result.get('retrieved_chunks', [])),
                'correctness': result['scores']['correctness'],
                'completeness': result['scores']['completeness'],
                'relevance': result['scores']['relevance'],
                'faithfulness': result['scores']['faithfulness'],
                'clarity': result['scores']['clarity'],
            }
            
            # Calculate average score
            score_columns = ['correctness', 'completeness', 'relevance', 'faithfulness', 'clarity']
            row['avg_score'] = np.mean([row[col] for col in score_columns])
            
            rows.append(row)
    
    return pd.DataFrame(rows)


def calculate_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate summary statistics for each method.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        
    Returns:
        DataFrame with summary statistics per method
    """
    stats = df.groupby('method').agg({
        'latency_ms': ['mean', 'std', 'min', 'max'],
        'num_chunks': ['mean', 'std', 'min', 'max'],
        'correctness': ['mean', 'std'],
        'completeness': ['mean', 'std'],
        'relevance': ['mean', 'std'],
        'faithfulness': ['mean', 'std'],
        'clarity': ['mean', 'std'],
        'avg_score': ['mean', 'std'],
    }).round(2)
    
    # Flatten multi-level columns
    stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
    stats = stats.reset_index()
    
    return stats


def compare_methods(results: Dict[str, Any]) -> pd.DataFrame:
    """Create comparison table of methods from summary data.
    
    Args:
        results: Loaded evaluation results dictionary
        
    Returns:
        DataFrame comparing methods across key metrics
    """
    summary = results.get('summary', {})
    
    comparison_data = []
    for method in ['naive_rag', 'kg_rag', 'hybrid_rag']:
        if method not in summary:
            continue
            
        method_data = summary[method]
        avg_scores = method_data.get('avg_scores', {})
        
        row = {
            'Method': method.replace('_', ' ').title(),
            'Avg Latency (ms)': round(method_data.get('avg_latency_ms', 0), 2),
            'Correctness': avg_scores.get('correctness', 0),
            'Completeness': avg_scores.get('completeness', 0),
            'Relevance': avg_scores.get('relevance', 0),
            'Faithfulness': avg_scores.get('faithfulness', 0),
            'Clarity': avg_scores.get('clarity', 0),
        }
        
        # Calculate overall average score
        score_cols = ['Correctness', 'Completeness', 'Relevance', 'Faithfulness', 'Clarity']
        row['Overall Score'] = round(np.mean([row[col] for col in score_cols]), 2)
        
        comparison_data.append(row)
    
    df = pd.DataFrame(comparison_data)
    
    # Add ranking column
    df['Rank (by Overall Score)'] = df['Overall Score'].rank(ascending=False, method='min').astype(int)
    
    # Reorder columns
    cols = ['Rank (by Overall Score)', 'Method', 'Overall Score', 'Correctness', 
            'Completeness', 'Relevance', 'Faithfulness', 'Clarity', 'Avg Latency (ms)']
    df = df[cols]
    
    return df.sort_values('Rank (by Overall Score)')


def generate_comparison_table(result_files: List[str | Path]) -> pd.DataFrame:
    """Generate comparison table from multiple evaluation result files.
    
    Args:
        result_files: List of paths to evaluation result JSON files
        
    Returns:
        DataFrame with aggregated comparison across all files
    """
    all_dfs = []
    
    for result_file in result_files:
        results = load_evaluation_results(result_file)
        df = extract_detailed_results_to_dataframe(results)
        
        # Add metadata
        df['dataset'] = results.get('dataset_name', 'unknown')
        df['evaluation_id'] = results.get('evaluation_id', 'unknown')
        
        all_dfs.append(df)
    
    # Combine all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    return combined_df


def calculate_per_question_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate metrics per question across all methods.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        
    Returns:
        DataFrame showing each question's performance across methods
    """
    # Pivot to show methods as columns
    metrics = []
    
    for question_id in df['question_id'].unique():
        question_data = df[df['question_id'] == question_id]
        
        row = {
            'question_id': question_id,
            'question_text': question_data.iloc[0]['question_text'][:60] + '...',  # Truncate
        }
        
        for method in question_data['method'].unique():
            method_data = question_data[question_data['method'] == method].iloc[0]
            row[f'{method}_score'] = method_data['avg_score']
            row[f'{method}_latency'] = round(method_data['latency_ms'], 2)
            row[f'{method}_chunks'] = method_data['num_chunks']
        
        metrics.append(row)
    
    return pd.DataFrame(metrics)


def calculate_score_differences(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate score differences between methods.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        
    Returns:
        DataFrame showing score improvements/degradations
    """
    pivot_df = df.pivot_table(
        index='question_id',
        columns='method',
        values='avg_score',
        aggfunc='mean'
    )
    
    differences = pd.DataFrame()
    
    if 'Naive Rag' in pivot_df.columns and 'Kg Rag' in pivot_df.columns:
        differences['KG vs Naive'] = pivot_df['Kg Rag'] - pivot_df['Naive Rag']
    
    if 'Naive Rag' in pivot_df.columns and 'Hybrid Rag' in pivot_df.columns:
        differences['Hybrid vs Naive'] = pivot_df['Hybrid Rag'] - pivot_df['Naive Rag']
    
    if 'Kg Rag' in pivot_df.columns and 'Hybrid Rag' in pivot_df.columns:
        differences['Hybrid vs KG'] = pivot_df['Hybrid Rag'] - pivot_df['Kg Rag']
    
    differences = differences.round(2)
    differences['question_id'] = differences.index
    
    return differences.reset_index(drop=True)


def export_to_csv(df: pd.DataFrame, output_path: str | Path) -> None:
    """Export DataFrame to CSV file.
    
    Args:
        df: DataFrame to export
        output_path: Path to output CSV file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved CSV to: {output_path}")


def generate_text_report(results: Dict[str, Any]) -> str:
    """Generate a text summary report of evaluation results.
    
    Args:
        results: Loaded evaluation results dictionary
        
    Returns:
        Formatted text report
    """
    report = []
    report.append("=" * 80)
    report.append("RAG EVALUATION REPORT")
    report.append("=" * 80)
    report.append(f"\nDataset: {results.get('dataset_name', 'unknown')}")
    report.append(f"Evaluation ID: {results.get('evaluation_id', 'unknown')}")
    report.append(f"Timestamp: {results.get('timestamp', 'unknown')}")
    report.append(f"Number of Questions: {results.get('num_questions', 0)}")
    report.append("\n")
    
    # Summary comparison
    df = compare_methods(results)
    report.append("-" * 80)
    report.append("METHOD COMPARISON")
    report.append("-" * 80)
    report.append(df.to_string(index=False))
    report.append("\n")
    
    # Detailed stats
    detailed_df = extract_detailed_results_to_dataframe(results)
    stats_df = calculate_summary_stats(detailed_df)
    report.append("-" * 80)
    report.append("DETAILED STATISTICS")
    report.append("-" * 80)
    report.append(stats_df.to_string(index=False))
    report.append("\n")
    
    # Key insights
    report.append("-" * 80)
    report.append("KEY INSIGHTS")
    report.append("-" * 80)
    
    # Best performer
    best_method = df.iloc[0]['Method']
    best_score = df.iloc[0]['Overall Score']
    report.append(f"• Best performing method: {best_method} (score: {best_score})")
    
    # Fastest method
    fastest_method = df.loc[df['Avg Latency (ms)'].idxmin(), 'Method']
    fastest_latency = df['Avg Latency (ms)'].min()
    report.append(f"• Fastest method: {fastest_method} ({fastest_latency:.2f} ms)")
    
    # Latency vs quality tradeoff
    if len(df) >= 2:
        latency_range = df['Avg Latency (ms)'].max() - df['Avg Latency (ms)'].min()
        score_range = df['Overall Score'].max() - df['Overall Score'].min()
        report.append(f"• Latency range: {latency_range:.2f} ms")
        report.append(f"• Score range: {score_range:.2f} points")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)
