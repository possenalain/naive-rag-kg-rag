"""
Evaluation orchestrator coordinating RAG benchmarking.
Runs all three variants and collects comprehensive metrics.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path
import json

from src.rag_variants.naive_rag import NaiveRAG
from src.rag_variants.kg_rag import KnowledgeGraphRAG
from src.rag_variants.hybrid_rag import HybridRAG
from src.evaluation.llm_scorer import LLMScorer
from src.utils.db import get_db
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EvaluationOrchestrator:
    """
    Orchestrates comprehensive RAG evaluation.
    
    Workflow:
    1. Load benchmark questions
    2. Run all three RAG variants
    3. Score answers using LLM
    4. Store results in database
    5. Generate summary statistics
    """
    
    def __init__(self):
        self.naive_rag = NaiveRAG()
        self.kg_rag = KnowledgeGraphRAG()
        self.hybrid_rag = HybridRAG()
        self.scorer = LLMScorer()
        self.db = None
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing evaluation orchestrator...")
        
        await self.naive_rag.initialize()
        await self.kg_rag.initialize()
        await self.hybrid_rag.initialize()
        await self.scorer.initialize()
        self.db = await get_db()
        
        logger.info("Evaluation orchestrator initialized")
    
    async def run_evaluation(
        self,
        dataset_name: str = "hotpotqa",
        num_questions: Optional[int] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline.
        
        Args:
            dataset_name: Benchmark dataset name
            num_questions: Number of questions to evaluate (None = all)
            output_dir: Directory to save results
        
        Returns:
            Summary statistics
        """
        if not self.db:
            await self.initialize()
        
        start_time = datetime.utcnow()
        logger.info(f"Starting evaluation on dataset: {dataset_name}")
        
        # Step 1: Load benchmark questions
        questions = await self.db.get_benchmark_questions(
            dataset_name=dataset_name,
            limit=num_questions or settings.benchmark.num_questions
        )
        
        if not questions:
            logger.error(f"No questions found for dataset: {dataset_name}")
            return {'status': 'failed', 'reason': 'No benchmark questions'}
        
        logger.info(f"Loaded {len(questions)} benchmark questions")
        
        # Step 2: Run all three RAG variants
        logger.info("Running Naive RAG...")
        naive_results = await self._run_rag_variant(
            self.naive_rag, questions, variant_name="naive"
        )
        
        logger.info("Running Knowledge Graph RAG...")
        kg_results = await self._run_rag_variant(
            self.kg_rag, questions, variant_name="kg"
        )
        
        logger.info("Running Hybrid RAG...")
        hybrid_results = await self._run_rag_variant(
            self.hybrid_rag, questions, variant_name="hybrid"
        )
        
        # Step 3: Score all answers
        logger.info("Scoring answers...")
        all_evaluations = naive_results + kg_results + hybrid_results
        
        scoring_data = [
            {
                'question': eval_item['question_text'],
                'ground_truth': eval_item['ground_truth'],
                'generated_answer': eval_item['generated_answer'],
                'retrieved_chunks': eval_item['retrieved_chunks']
            }
            for eval_item in all_evaluations
        ]
        
        scores = await self.scorer.batch_score(scoring_data)
        
        # Step 4: Store scores in database
        logger.info("Storing evaluation results...")
        for eval_item, score in zip(all_evaluations, scores):
            # Store scores
            await self.db.insert_scores(
                evaluation_id=eval_item['evaluation_id'],
                correctness=score['correctness'],
                completeness=score['completeness'],
                relevance=score['relevance'],
                faithfulness=score['faithfulness'],
                clarity=score['clarity'],
                explanation={
                    'correctness': score.get('correctness_explanation', ''),
                    'completeness': score.get('completeness_explanation', ''),
                    'relevance': score.get('relevance_explanation', ''),
                    'faithfulness': score.get('faithfulness_explanation', ''),
                    'clarity': score.get('clarity_explanation', ''),
                    'overall': score.get('overall_assessment', '')
                }
            )
        
        # Step 5: Compute summary statistics
        logger.info("Computing summary statistics...")
        summary = self._compute_summary(naive_results, kg_results, hybrid_results, scores)
        
        # Step 6: Save results to file
        if output_dir:
            output_path = Path(output_dir) / f"evaluation_{dataset_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Results saved to: {output_path}")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        summary['duration_seconds'] = duration
        summary['status'] = 'success'
        
        logger.info(f"Evaluation complete in {duration:.2f}s")
        return summary
    
    async def _run_rag_variant(
        self,
        rag_system,
        questions: List[Dict[str, Any]],
        variant_name: str
    ) -> List[Dict[str, Any]]:
        """Run a single RAG variant on all questions."""
        results = []
        
        for question_data in questions:
            question_text = question_data['question_text']
            question_id = question_data['id']
            
            try:
                # Generate answer
                result = await rag_system.generate(question_text)
                
                # Store evaluation
                eval_id = await self.db.insert_evaluation(
                    rag_variant=variant_name,
                    question_id=question_id,
                    generated_answer=result['answer'],
                    retrieved_chunks=result['chunk_ids'],
                    latency_ms=result['latency_ms'],
                    metadata={
                        'fusion_strategy': result.get('fusion_strategy'),
                        'error': result.get('error')
                    }
                )
                
                results.append({
                    'evaluation_id': eval_id,
                    'question_text': question_text,
                    'ground_truth': question_data['ground_truth'],
                    'generated_answer': result['answer'],
                    'retrieved_chunks': result['retrieved_chunks'],
                    'latency_ms': result['latency_ms'],
                    'variant': variant_name
                })
                
            except Exception as e:
                logger.error(f"Error running {variant_name} on question {question_id}: {e}")
                continue
        
        logger.info(f"{variant_name.upper()}: {len(results)}/{len(questions)} questions completed")
        return results
    
    def _compute_summary(
        self,
        naive_results: List[Dict[str, Any]],
        kg_results: List[Dict[str, Any]],
        hybrid_results: List[Dict[str, Any]],
        scores: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compute summary statistics."""
        n_naive = len(naive_results)
        n_kg = len(kg_results)
        n_hybrid = len(hybrid_results)
        
        # Split scores by variant
        naive_scores = scores[:n_naive]
        kg_scores = scores[n_naive:n_naive + n_kg]
        hybrid_scores = scores[n_naive + n_kg:]
        
        def avg_scores(score_list):
            if not score_list:
                return {}
            return {
                'correctness': sum(s['correctness'] for s in score_list) / len(score_list),
                'completeness': sum(s['completeness'] for s in score_list) / len(score_list),
                'relevance': sum(s['relevance'] for s in score_list) / len(score_list),
                'faithfulness': sum(s['faithfulness'] for s in score_list) / len(score_list),
                'clarity': sum(s['clarity'] for s in score_list) / len(score_list),
            }
        
        def avg_latency(result_list):
            if not result_list:
                return 0
            return sum(r['latency_ms'] for r in result_list) / len(result_list)
        
        return {
            'naive_rag': {
                'num_questions': n_naive,
                'avg_latency_ms': avg_latency(naive_results),
                'avg_scores': avg_scores(naive_scores)
            },
            'kg_rag': {
                'num_questions': n_kg,
                'avg_latency_ms': avg_latency(kg_results),
                'avg_scores': avg_scores(kg_scores)
            },
            'hybrid_rag': {
                'num_questions': n_hybrid,
                'avg_latency_ms': avg_latency(hybrid_results),
                'avg_scores': avg_scores(hybrid_scores)
            }
        }


# Example usage
if __name__ == "__main__":
    async def test_evaluation():
        logging.basicConfig(level=logging.INFO)
        
        orchestrator = EvaluationOrchestrator()
        await orchestrator.initialize()
        
        summary = await orchestrator.run_evaluation(
            dataset_name="hotpotqa",
            num_questions=10,
            output_dir="./benchmarks/results"
        )
        
        print("\n=== Evaluation Summary ===")
        print(json.dumps(summary, indent=2))
    
    asyncio.run(test_evaluation())
