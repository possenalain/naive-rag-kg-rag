"""
Command Line Interface for RAG Benchmarking System.
Provides commands for ingestion, evaluation, and analysis.
"""

import asyncio
import click
import logging
from pathlib import Path
import sys
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.pipeline import IngestionPipeline
from src.evaluation.orchestrator import EvaluationOrchestrator
from src.utils.db import get_db
from src.utils.graph import get_graph
from src.utils.logging_config import setup_logging, setup_quiet_loggers
from config.settings import get_settings

# Setup logging with file output
setup_logging(
    log_level="INFO",
    log_dir="./logs",
    log_to_file=True,
    log_to_console=True
)
setup_quiet_loggers()

logger = logging.getLogger(__name__)
settings = get_settings()


@click.group()
def cli():
    """RAG Benchmarking CLI - Compare Naive, KG, and Hybrid RAG approaches."""
    pass


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--chunk-size', default=512, help='Target chunk size in tokens')
@click.option('--chunk-overlap', default=50, help='Overlap between chunks')
@click.option('--enable-kg/--no-kg', default=True, help='Build knowledge graph')
@click.option('--recursive/--no-recursive', default=True, help='Recursive directory scan')
def ingest(directory, chunk_size, chunk_overlap, enable_kg, recursive):
    """Ingest documents from DIRECTORY."""
    async def run():
        logger.info(f"Starting ingestion from: {directory}")
        
        pipeline = IngestionPipeline(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_kg=enable_kg
        )
        await pipeline.initialize()
        
        stats = await pipeline.ingest_directory(
            directory=Path(directory),
            recursive=recursive
        )
        
        click.echo("\n✓ Ingestion Complete!")
        click.echo(f"  Documents: {stats['documents_processed']}")
        click.echo(f"  Chunks: {stats['chunks_created']}")
        click.echo(f"  Duration: {stats['duration_seconds']:.2f}s")
        
        if enable_kg:
            click.echo(f"  KG Entities: {stats['knowledge_graph']['entities_created']}")
    
    asyncio.run(run())


@cli.command()
@click.option('--dataset', default='factual_questions', help='Benchmark dataset name (without .json)')
@click.option('--dataset-path', default=None, help='Explicit path to benchmark JSON file')
@click.option('--num-questions', default=50, type=int, help='Number of questions')
@click.option('--output-dir', default='./benchmarks/results', help='Output directory')
def evaluate(dataset, dataset_path, num_questions, output_dir):
    """Run evaluation on benchmark dataset."""
    async def run():
        logger.info(f"Starting evaluation on {dataset}")
        
        orchestrator = EvaluationOrchestrator()
        await orchestrator.initialize()
        
        summary = await orchestrator.run_evaluation(
            dataset_name=dataset,
            dataset_path=dataset_path,
            num_questions=num_questions,
            output_dir=output_dir
        )
        
        click.echo("\n✓ Evaluation Complete!")
        click.echo(f"  Duration: {summary['duration_seconds']:.2f}s")
        
        click.echo("\n=== Naive RAG ===")
        naive = summary['naive_rag']
        click.echo(f"  Avg Latency: {naive['avg_latency_ms']:.2f}ms")
        click.echo(f"  Avg Scores:")
        for dim, score in naive['avg_scores'].items():
            click.echo(f"    {dim.capitalize()}: {score:.2f}/5")
        
        click.echo("\n=== Knowledge Graph RAG ===")
        kg = summary['kg_rag']
        click.echo(f"  Avg Latency: {kg['avg_latency_ms']:.2f}ms")
        click.echo(f"  Avg Scores:")
        for dim, score in kg['avg_scores'].items():
            click.echo(f"    {dim.capitalize()}: {score:.2f}/5")
        
        click.echo("\n=== Hybrid RAG ===")
        hybrid = summary['hybrid_rag']
        click.echo(f"  Avg Latency: {hybrid['avg_latency_ms']:.2f}ms")
        click.echo(f"  Avg Scores:")
        for dim, score in hybrid['avg_scores'].items():
            click.echo(f"    {dim.capitalize()}: {score:.2f}/5")
    
    asyncio.run(run())


@cli.command()
@click.argument('question')
@click.option('--variant', type=click.Choice(['naive', 'kg', 'hybrid']), default='hybrid')
@click.option('--top-k', default=5, type=int, help='Number of chunks to retrieve')
def query(question, variant, top_k):
    """Ask a question using specified RAG variant."""
    async def run():
        from src.rag_variants.naive_rag import NaiveRAG
        from src.rag_variants.kg_rag import KnowledgeGraphRAG
        from src.rag_variants.hybrid_rag import HybridRAG
        
        # Initialize appropriate RAG system
        if variant == 'naive':
            rag = NaiveRAG(top_k=top_k)
        elif variant == 'kg':
            rag = KnowledgeGraphRAG(top_k=top_k)
        else:
            rag = HybridRAG(top_k=top_k)
        
        await rag.initialize()
        
        click.echo(f"\nQuery ({variant.upper()} RAG): {question}")
        click.echo("Generating answer...")
        
        result = await rag.generate(question)
        
        click.echo(f"\n{result['answer']}")
        click.echo(f"\n[Retrieved {len(result['retrieved_chunks'])} chunks in {result['latency_ms']:.2f}ms]")
    
    asyncio.run(run())


@cli.command()
def status():
    """Show system status and statistics."""
    async def run():
        db = await get_db()
        graph = await get_graph()
        
        # Database stats
        docs = await db.list_documents(limit=1000)
        
        # Graph stats
        graph_stats = await graph.get_graph_stats()
        
        click.echo("\n=== System Status ===")
        click.echo(f"  Documents: {len(docs)}")
        click.echo(f"  Graph Chunks: {graph_stats.get('chunk_count', 0)}")
        click.echo(f"  Graph Entities: {graph_stats.get('entity_count', 0)}")
        click.echo(f"  Entity Relations: {graph_stats.get('entity_relations', 0)}")
        
        # Check for evaluations (now in local files)
        click.echo(f"\n  Evaluation: Results stored in local files")
        results_dir = Path("./benchmarks/results")
        if results_dir.exists():
            eval_files = list(results_dir.glob("eval_*.json"))
            click.echo(f"  Evaluation files: {len(eval_files)}")
        else:
            click.echo(f"  Evaluation files: 0")
    
    asyncio.run(run())


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset all data?')
def reset():
    """Reset database and graph (WARNING: Deletes all data)."""
    async def run():
        db = await get_db()
        graph = await get_graph()
        
        # Clear graph
        result = await graph.clear_graph()
        click.echo(f"✓ Cleared graph: {result['deleted_count']} nodes")
        
        # Clear database tables (keeping schema)
        async with db.connection() as conn:
            await conn.execute("TRUNCATE TABLE scores CASCADE")
            await conn.execute("TRUNCATE TABLE evaluations CASCADE")
            await conn.execute("TRUNCATE TABLE chunks CASCADE")
            await conn.execute("TRUNCATE TABLE documents CASCADE")
            await conn.execute("TRUNCATE TABLE benchmark_questions CASCADE")
        
        click.echo("✓ Cleared database tables")
        click.echo("\nSystem reset complete!")
    
    asyncio.run(run())


@cli.command()
@click.option('--name', default=None, help='Custom backup name')
@click.option('--postgres-only', is_flag=True, help='Backup PostgreSQL only')
@click.option('--neo4j-only', is_flag=True, help='Backup Neo4j only')
def backup(name, postgres_only, neo4j_only):
    """Create backup of databases.
    
    Backups are stored in ./db/backups/ directory.
    """
    async def run():
        from src.utils.backup import backup_postgres, backup_neo4j
        
        backup_dir = Path('./db/backups')
        
        click.echo("\n" + "="*80)
        click.echo("DATABASE BACKUP")
        click.echo("="*80 + "\n")
        
        # Backup PostgreSQL
        if not neo4j_only:
            try:
                await backup_postgres(backup_dir, name)
            except Exception as e:
                click.echo(f"✗ PostgreSQL backup failed: {e}", err=True)
                if not postgres_only:
                    click.echo("Continuing with Neo4j backup...")
        
        # Backup Neo4j
        if not postgres_only:
            try:
                click.echo("")
                await backup_neo4j(backup_dir, name)
            except Exception as e:
                click.echo(f"✗ Neo4j backup failed: {e}", err=True)
        
        click.echo("\n" + "="*80)
        click.echo(f"✓ Backups saved to: {backup_dir.absolute()}")
        click.echo("="*80)
    
    asyncio.run(run())


@cli.command()
@click.option('--postgres-backup', type=click.Path(exists=True), help='PostgreSQL backup file (.sql)')
@click.option('--neo4j-backup', type=click.Path(exists=True), help='Neo4j backup file (.cypher)')
@click.option('--list-backups', is_flag=True, help='List available backups')
@click.confirmation_option(prompt='Are you sure? This will replace current data.')
def restore(postgres_backup, neo4j_backup, list_backups):
    """Restore databases from backup.
    
    Examples:
        # List available backups
        python cli.py restore --list-backups
        
        # Restore both databases
        python cli.py restore --postgres-backup db/backups/postgres_backup_20260110.sql --neo4j-backup db/backups/neo4j_backup_20260110.cypher
        
        # Restore only PostgreSQL
        python cli.py restore --postgres-backup db/backups/postgres_backup_20260110.sql
    """
    async def run():
        from src.utils.backup import restore_postgres, restore_neo4j, list_backups as list_backup_files
        
        backup_dir = Path('./db/backups')
        
        # List backups if requested
        if list_backups:
            click.echo("\n" + "="*80)
            click.echo("AVAILABLE BACKUPS")
            click.echo("="*80 + "\n")
            
            backups = await list_backup_files(backup_dir)
            
            if not backups:
                click.echo("No backups found in ./db/backups/")
                return
            
            for backup in backups:
                click.echo(f"Name: {backup.get('backup_name')}")
                click.echo(f"Time: {backup.get('backup_time')}")
                
                if 'document_count' in backup:
                    click.echo(f"Type: PostgreSQL")
                    click.echo(f"  Documents: {backup.get('document_count')}")
                    click.echo(f"  Chunks: {backup.get('chunk_count')}")
                else:
                    click.echo(f"Type: Neo4j")
                    click.echo(f"  Nodes: {backup.get('node_count')}")
                    click.echo(f"  Entities: {backup.get('entity_count')}")
                
                click.echo("")
            
            return
        
        # Restore from backups
        if not postgres_backup and not neo4j_backup:
            click.echo("Error: Specify --postgres-backup and/or --neo4j-backup", err=True)
            click.echo("Or use --list-backups to see available backups")
            return
        
        click.echo("\n" + "="*80)
        click.echo("DATABASE RESTORE")
        click.echo("="*80 + "\n")
        
        # Restore PostgreSQL
        if postgres_backup:
            try:
                await restore_postgres(Path(postgres_backup))
            except Exception as e:
                click.echo(f"✗ PostgreSQL restore failed: {e}", err=True)
        
        # Restore Neo4j
        if neo4j_backup:
            try:
                if postgres_backup:
                    click.echo("")
                await restore_neo4j(Path(neo4j_backup))
            except Exception as e:
                click.echo(f"✗ Neo4j restore failed: {e}", err=True)
        
        click.echo("\n" + "="*80)
        click.echo("✓ Restore complete!")
        click.echo("="*80)
    
    asyncio.run(run())


@cli.command()
@click.argument('result_files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('--output-dir', default='./benchmarks/results', help='Output directory for figures and CSVs')
@click.option('--show-plots/--no-show-plots', default=False, help='Display plots interactively')
@click.option('--format', type=click.Choice(['png', 'pdf', 'svg']), default='png', help='Figure format')
def analyze(result_files, output_dir, show_plots, format):
    """Analyze evaluation results and generate visualizations.
    
    RESULT_FILES: One or more evaluation result JSON files to analyze.
    
    Example:
        python cli.py analyze benchmarks/results/eval_*.json
        python cli.py analyze benchmarks/results/eval_20260110_*.json --output-dir ./analysis_output
    """
    from src.analysis.metrics import (
        load_evaluation_results,
        extract_detailed_results_to_dataframe,
        calculate_summary_stats,
        compare_methods,
        generate_text_report,
        export_to_csv,
    )
    from src.analysis.visualizations import (
        plot_score_comparison,
        plot_latency_comparison,
        plot_chunk_count_distribution,
        plot_comprehensive_comparison,
        plot_per_question_heatmap,
    )
    import matplotlib.pyplot as plt
    
    output_path = Path(output_dir)
    figures_path = output_path / 'figures'
    figures_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"\n{'='*80}")
    click.echo("RAG EVALUATION ANALYSIS")
    click.echo(f"{'='*80}\n")
    click.echo(f"Analyzing {len(result_files)} result file(s)...")
    
    # Load all results
    all_dfs = []
    for result_file in result_files:
        click.echo(f"  Loading: {Path(result_file).name}")
        results = load_evaluation_results(result_file)
        df = extract_detailed_results_to_dataframe(results)
        df['source_file'] = Path(result_file).name
        all_dfs.append(df)
    
    # Combine all data
    combined_df = pd.concat(all_dfs, ignore_index=True) if len(all_dfs) > 1 else all_dfs[0]
    
    click.echo(f"\n✓ Loaded {len(combined_df)} total result entries")
    click.echo(f"  Methods: {', '.join(combined_df['method'].unique())}")
    click.echo(f"  Questions: {combined_df['question_id'].nunique()}")
    
    # Generate text report
    click.echo(f"\n{'='*80}")
    click.echo("GENERATING REPORT")
    click.echo(f"{'='*80}")
    
    # Use first result file for main report
    main_results = load_evaluation_results(result_files[0])
    report_text = generate_text_report(main_results)
    click.echo(report_text)
    
    # Save report
    report_path = output_path / 'analysis_report.txt'
    report_path.write_text(report_text)
    click.echo(f"\n✓ Saved text report to: {report_path}")
    
    # Export CSVs
    click.echo(f"\n{'='*80}")
    click.echo("EXPORTING DATA")
    click.echo(f"{'='*80}")
    
    # Detailed results CSV
    detailed_csv = output_path / 'detailed_results.csv'
    export_to_csv(combined_df, detailed_csv)
    
    # Summary statistics CSV
    summary_stats = calculate_summary_stats(combined_df)
    summary_csv = output_path / 'summary_statistics.csv'
    export_to_csv(summary_stats, summary_csv)
    
    # Method comparison CSV
    comparison_df = compare_methods(main_results)
    comparison_csv = output_path / 'method_comparison.csv'
    export_to_csv(comparison_df, comparison_csv)
    
    # Generate visualizations
    click.echo(f"\n{'='*80}")
    click.echo("GENERATING VISUALIZATIONS")
    click.echo(f"{'='*80}")
    
    figures = [
        ('score_comparison', lambda: plot_score_comparison(combined_df)),
        ('latency_comparison', lambda: plot_latency_comparison(combined_df)),
        ('chunk_distribution', lambda: plot_chunk_count_distribution(combined_df)),
        ('comprehensive_dashboard', lambda: plot_comprehensive_comparison(combined_df)),
        ('question_heatmap', lambda: plot_per_question_heatmap(combined_df)),
    ]
    
    saved_figures = []
    for fig_name, plot_func in figures:
        fig_path = figures_path / f'{fig_name}.{format}'
        click.echo(f"  Generating {fig_name}...")
        
        fig = plot_func()
        plt.savefig(fig_path, dpi=300, bbox_inches='tight', format=format)
        
        if not show_plots:
            plt.close(fig)
        
        saved_figures.append(fig_path)
        click.echo(f"    ✓ Saved: {fig_path}")
    
    # Show plots if requested
    if show_plots:
        click.echo("\nDisplaying plots...")
        plt.show()
    
    # Summary
    click.echo(f"\n{'='*80}")
    click.echo("ANALYSIS COMPLETE")
    click.echo(f"{'='*80}")
    click.echo(f"\nGenerated {len(saved_figures)} figures:")
    for fig_path in saved_figures:
        click.echo(f"  - {fig_path}")
    
    click.echo(f"\nExported {3} CSV files:")
    click.echo(f"  - {detailed_csv}")
    click.echo(f"  - {summary_csv}")
    click.echo(f"  - {comparison_csv}")
    
    click.echo(f"\nAll outputs saved to: {output_path}")


if __name__ == '__main__':
    cli()
