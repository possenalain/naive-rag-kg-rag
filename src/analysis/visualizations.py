"""Visualization functions for RAG evaluation results."""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10


def plot_score_comparison(df: pd.DataFrame, save_path: str | Path = None) -> plt.Figure:
    """Plot comparison of scores across methods.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Score Comparison Across RAG Methods', fontsize=16, fontweight='bold')
    
    score_columns = ['correctness', 'completeness', 'relevance', 'faithfulness', 'clarity', 'avg_score']
    titles = ['Correctness', 'Completeness', 'Relevance', 'Faithfulness', 'Clarity', 'Overall Average']
    
    for idx, (col, title) in enumerate(zip(score_columns, titles)):
        ax = axes[idx // 3, idx % 3]
        
        # Create bar plot
        data = df.groupby('method')[col].mean().reset_index()
        bars = ax.bar(data['method'], data[col], color=['#3498db', '#e74c3c', '#2ecc71'])
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('Score (1-5)')
        ax.set_title(title, fontweight='bold')
        ax.set_ylim(0, 5.5)
        ax.grid(axis='y', alpha=0.3)
        
        # Rotate x labels
        ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    return fig


def plot_latency_comparison(df: pd.DataFrame, save_path: str | Path = None) -> plt.Figure:
    """Plot latency comparison across methods.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Latency Comparison Across RAG Methods', fontsize=16, fontweight='bold')
    
    # Bar plot of average latency
    avg_latency = df.groupby('method')['latency_ms'].mean().reset_index()
    bars = ax1.bar(avg_latency['method'], avg_latency['latency_ms'], 
                   color=['#3498db', '#e74c3c', '#2ecc71'])
    
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}ms',
                ha='center', va='bottom', fontweight='bold')
    
    ax1.set_ylabel('Average Latency (ms)')
    ax1.set_title('Average Latency by Method', fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Box plot showing distribution
    methods = df['method'].unique()
    data_to_plot = [df[df['method'] == method]['latency_ms'].values for method in methods]
    
    bp = ax2.boxplot(data_to_plot, labels=methods, patch_artist=True,
                     boxprops=dict(facecolor='lightblue', alpha=0.7),
                     medianprops=dict(color='red', linewidth=2))
    
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title('Latency Distribution', fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    return fig


def plot_chunk_count_distribution(df: pd.DataFrame, save_path: str | Path = None) -> plt.Figure:
    """Plot distribution of retrieved chunk counts.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Retrieved Chunks Analysis', fontsize=16, fontweight='bold')
    
    # Average chunks per method
    avg_chunks = df.groupby('method')['num_chunks'].mean().reset_index()
    bars = ax1.bar(avg_chunks['method'], avg_chunks['num_chunks'],
                   color=['#3498db', '#e74c3c', '#2ecc71'])
    
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontweight='bold')
    
    ax1.set_ylabel('Average Number of Chunks')
    ax1.set_title('Average Chunks Retrieved', fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Distribution by question
    for method in df['method'].unique():
        method_data = df[df['method'] == method]
        ax2.plot(method_data['question_id'], method_data['num_chunks'], 
                marker='o', label=method, linewidth=2)
    
    ax2.set_xlabel('Question ID')
    ax2.set_ylabel('Number of Chunks')
    ax2.set_title('Chunks Retrieved per Question', fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    return fig


def plot_comprehensive_comparison(df: pd.DataFrame, save_path: str | Path = None) -> plt.Figure:
    """Create comprehensive comparison dashboard.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Comprehensive RAG Method Comparison Dashboard', 
                 fontsize=18, fontweight='bold')
    
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. Overall scores (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    avg_scores = df.groupby('method')['avg_score'].mean().reset_index()
    bars = ax1.barh(avg_scores['method'], avg_scores['avg_score'],
                    color=['#3498db', '#e74c3c', '#2ecc71'])
    for bar in bars:
        width = bar.get_width()
        ax1.text(width, bar.get_y() + bar.get_height()/2.,
                f'{width:.2f}',
                ha='left', va='center', fontweight='bold')
    ax1.set_xlabel('Score')
    ax1.set_title('Overall Scores', fontweight='bold')
    ax1.set_xlim(0, 5.5)
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Latency (top middle)
    ax2 = fig.add_subplot(gs[0, 1])
    avg_latency = df.groupby('method')['latency_ms'].mean().reset_index()
    bars = ax2.barh(avg_latency['method'], avg_latency['latency_ms'],
                    color=['#3498db', '#e74c3c', '#2ecc71'])
    for bar in bars:
        width = bar.get_width()
        ax2.text(width, bar.get_y() + bar.get_height()/2.,
                f'{width:.0f}ms',
                ha='left', va='center', fontweight='bold')
    ax2.set_xlabel('Latency (ms)')
    ax2.set_title('Average Latency', fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # 3. Chunks (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    avg_chunks = df.groupby('method')['num_chunks'].mean().reset_index()
    bars = ax3.barh(avg_chunks['method'], avg_chunks['num_chunks'],
                    color=['#3498db', '#e74c3c', '#2ecc71'])
    for bar in bars:
        width = bar.get_width()
        ax3.text(width, bar.get_y() + bar.get_height()/2.,
                f'{width:.1f}',
                ha='left', va='center', fontweight='bold')
    ax3.set_xlabel('Chunks')
    ax3.set_title('Avg Chunks Retrieved', fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)
    
    # 4. Score breakdown radar (middle left, spans 2 cols)
    ax4 = fig.add_subplot(gs[1, :2], projection='polar')
    categories = ['Correctness', 'Completeness', 'Relevance', 'Faithfulness', 'Clarity']
    score_cols = ['correctness', 'completeness', 'relevance', 'faithfulness', 'clarity']
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]
    
    colors = ['#3498db', '#e74c3c', '#2ecc71']
    for idx, method in enumerate(df['method'].unique()):
        method_data = df[df['method'] == method][score_cols].mean().tolist()
        method_data += method_data[:1]
        ax4.plot(angles, method_data, 'o-', linewidth=2, label=method, color=colors[idx])
        ax4.fill(angles, method_data, alpha=0.15, color=colors[idx])
    
    ax4.set_xticks(angles[:-1])
    ax4.set_xticklabels(categories)
    ax4.set_ylim(0, 5)
    ax4.set_title('Score Breakdown', fontweight='bold', pad=20)
    ax4.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax4.grid(True)
    
    # 5. Latency vs Score scatter (middle right)
    ax5 = fig.add_subplot(gs[1, 2])
    for method, color in zip(df['method'].unique(), colors):
        method_data = df[df['method'] == method]
        ax5.scatter(method_data['latency_ms'], method_data['avg_score'],
                   label=method, alpha=0.6, s=100, color=color)
    ax5.set_xlabel('Latency (ms)')
    ax5.set_ylabel('Average Score')
    ax5.set_title('Latency vs Quality', fontweight='bold')
    ax5.legend()
    ax5.grid(alpha=0.3)
    
    # 6. Score distribution violin plot (bottom, spans all)
    ax6 = fig.add_subplot(gs[2, :])
    methods = df['method'].unique()
    data_to_plot = [df[df['method'] == method]['avg_score'].values for method in methods]
    
    parts = ax6.violinplot(data_to_plot, positions=range(len(methods)),
                           showmeans=True, showmedians=True)
    
    for pc, color in zip(parts['bodies'], colors):
        pc.set_facecolor(color)
        pc.set_alpha(0.5)
    
    ax6.set_xticks(range(len(methods)))
    ax6.set_xticklabels(methods, rotation=45)
    ax6.set_ylabel('Score Distribution')
    ax6.set_title('Score Distribution by Method', fontweight='bold')
    ax6.grid(axis='y', alpha=0.3)
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    return fig


def plot_per_question_heatmap(df: pd.DataFrame, save_path: str | Path = None) -> plt.Figure:
    """Create heatmap showing performance per question.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Pivot data for heatmap
    pivot_data = df.pivot_table(
        index='question_id',
        columns='method',
        values='avg_score',
        aggfunc='mean'
    )
    
    # Create heatmap
    sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='RdYlGn',
                vmin=0, vmax=5, linewidths=1, ax=ax,
                cbar_kws={'label': 'Average Score'})
    
    ax.set_title('Score Heatmap: Questions vs Methods', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Method', fontweight='bold')
    ax.set_ylabel('Question ID', fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved figure to: {save_path}")
    
    return fig


def save_all_figures(df: pd.DataFrame, output_dir: str | Path) -> List[Path]:
    """Generate and save all visualization figures.
    
    Args:
        df: DataFrame from extract_detailed_results_to_dataframe
        output_dir: Directory to save figures
        
    Returns:
        List of paths to saved figures
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved_paths = []
    
    # Generate all plots
    plots = [
        ('score_comparison.png', lambda: plot_score_comparison(df)),
        ('latency_comparison.png', lambda: plot_latency_comparison(df)),
        ('chunk_distribution.png', lambda: plot_chunk_count_distribution(df)),
        ('comprehensive_dashboard.png', lambda: plot_comprehensive_comparison(df)),
        ('question_heatmap.png', lambda: plot_per_question_heatmap(df)),
    ]
    
    for filename, plot_func in plots:
        save_path = output_dir / filename
        plot_func()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        saved_paths.append(save_path)
        print(f"Saved: {save_path}")
    
    return saved_paths
