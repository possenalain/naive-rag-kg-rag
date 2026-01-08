"""
Command Line Interface for RAG Benchmarking System.
Provides commands for ingestion, evaluation, and analysis.
"""

import asyncio
import click
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.pipeline import IngestionPipeline
from src.evaluation.orchestrator import EvaluationOrchestrator
from src.utils.db import get_db
from src.utils.graph import get_graph
from config.settings import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
@click.option('--dataset', default='hotpotqa', help='Benchmark dataset name')
@click.option('--num-questions', default=50, type=int, help='Number of questions')
@click.option('--output-dir', default='./benchmarks/results', help='Output directory')
def evaluate(dataset, num_questions, output_dir):
    """Run evaluation on benchmark dataset."""
    async def run():
        logger.info(f"Starting evaluation on {dataset}")
        
        orchestrator = EvaluationOrchestrator()
        await orchestrator.initialize()
        
        summary = await orchestrator.run_evaluation(
            dataset_name=dataset,
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
        
        # Check for evaluations
        evals = await db.get_evaluation_results()
        if evals:
            click.echo(f"  Evaluations: {len(evals)}")
    
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


if __name__ == '__main__':
    cli()
