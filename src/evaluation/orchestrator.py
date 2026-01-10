"""
Evaluation orchestrator coordinating RAG benchmarking.
Runs all three variants and collects comprehensive metrics.
Loads questions from JSON files and saves results locally.
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path
import json
import uuid

from src.rag_variants.naive_rag import NaiveRAG
from src.rag_variants.kg_rag import KnowledgeGraphRAG
from src.rag_variants.hybrid_rag import HybridRAG
from src.evaluation.llm_scorer import LLMScorer
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EvaluationOrchestrator:
    """
    Orchestrates comprehensive RAG evaluation.
    
    Workflow:
    1. Load benchmark questions from JSON file
    2. Run all three RAG variants
    3. Score answers using LLM
    4. Save results to local JSON file
    5. Generate summary statistics
    """
    
    def __init__(self):
        self.naive_rag = NaiveRAG()
        self.kg_rag = KnowledgeGraphRAG()
        self.hybrid_rag = HybridRAG()
        self.scorer = LLMScorer()
        self.eval_id = None
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing evaluation orchestrator...")
        
        await self.naive_rag.initialize()
        await self.kg_rag.initialize()
        await self.hybrid_rag.initialize()
        await self.scorer.initialize()
        
        # Generate unique evaluation ID
        self.eval_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S') + "_" + str(uuid.uuid4())[:8]
        
        logger.info("Evaluation orchestrator initialized")
    
    async def run_evaluation(
        self,
        dataset_name: str = "factual_questions",
        dataset_path: Optional[str] = None,
        num_questions: Optional[int] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline.
        
        Args:
            dataset_name: Benchmark dataset name (without .json extension)
            dataset_path: Explicit path to benchmark JSON file (overrides dataset_name)
            num_questions: Number of questions to evaluate (None = all)
            output_dir: Directory to save results
        
        Returns:
            Summary statistics
        """
        if self.eval_id is None:
            await self.initialize()
        
        start_time = datetime.utcnow()
        logger.info(f"Starting evaluation on dataset: {dataset_name}")
        
        # Step 1: Load benchmark questions from JSON file
        questions = self._load_questions_from_json(
            dataset_name=dataset_name,
            dataset_path=dataset_path,
            num_questions=num_questions
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
                'retrieved_chunks': eval_item.get('retrieved_chunks', [])
            }
            for eval_item in all_evaluations
        ]
        
        scores = await self.scorer.batch_score(scoring_data)
        
        # Step 4: Attach scores to evaluations
        logger.info("Attaching scores to evaluations...")
        for eval_item, score in zip(all_evaluations, scores):
            eval_item['scores'] = {
                'correctness': score['correctness'],
                'completeness': score['completeness'],
                'relevance': score['relevance'],
                'faithfulness': score['faithfulness'],
                'clarity': score['clarity'],
                'explanations': {
                    'correctness': score.get('correctness_explanation', ''),
                    'completeness': score.get('completeness_explanation', ''),
                    'relevance': score.get('relevance_explanation', ''),
                    'faithfulness': score.get('faithfulness_explanation', ''),
                    'clarity': score.get('clarity_explanation', ''),
                    'overall': score.get('overall_assessment', '')
                }
            }
        
        # Step 5: Compute summary statistics
        logger.info("Computing summary statistics...")
        summary = self._compute_summary(naive_results, kg_results, hybrid_results, scores)
        
        # Step 6: Save results to local file
        output_dir = output_dir or settings.benchmark.output_dir
        results_data = {
            'evaluation_id': self.eval_id,
            'dataset_name': dataset_name,
            'dataset_path': dataset_path,
            'num_questions': len(questions),
            'timestamp': start_time.isoformat(),
            'summary': summary,
            'detailed_results': {
                'naive_rag': naive_results,
                'kg_rag': kg_results,
                'hybrid_rag': hybrid_results
            }
        }
        
        output_path = self._save_results(results_data, dataset_name, output_dir)
        logger.info(f"Results saved to: {output_path}")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        summary['duration_seconds'] = duration
        summary['status'] = 'success'
        summary['output_path'] = str(output_path)
        
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
        
        for idx, question_data in enumerate(questions):
            question_text = question_data['question_text']
            question_id = question_data.get('question_id', f"q_{idx}")
            
            try:
                # Generate answer
                result = await rag_system.generate(question_text)
                
                # Create evaluation entry
                eval_entry = {
                    'question_id': question_id,
                    'question_text': question_text,
                    'ground_truth': question_data.get('ground_truth', ''),
                    'generated_answer': result['answer'],
                    'retrieved_chunks': result.get('retrieved_chunks', []),
                    'latency_ms': result['latency_ms'],
                    'variant': variant_name,
                    'metadata': question_data.get('metadata', {}),
                    'source_documents': question_data.get('source_documents', [])
                }
                
                results.append(eval_entry)
                
            except Exception as e:
                logger.error(f"Error running {variant_name} on question {question_id}: {e}")
                # Add failed entry
                results.append({
                    'question_id': question_id,
                    'question_text': question_text,
                    'ground_truth': question_data.get('ground_truth', ''),
                    'generated_answer': '',
                    'retrieved_chunks': [],
                    'latency_ms': 0,
                    'variant': variant_name,
                    'error': str(e),
                    'metadata': question_data.get('metadata', {}),
                    'source_documents': question_data.get('source_documents', [])
                })
        
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
    
    def _load_questions_from_json(
        self,
        dataset_name: str,
        dataset_path: Optional[str] = None,
        num_questions: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Load questions from JSON benchmark file.
        
        Args:
            dataset_name: Name of dataset (without .json)
            dataset_path: Explicit path to JSON file (overrides dataset_name)
            num_questions: Limit number of questions (None = all)
        
        Returns:
            List of question dictionaries
        """
        # Determine file path
        if dataset_path:
            file_path = Path(dataset_path)
        else:
            datasets_dir = Path(settings.benchmark.datasets_dir)
            file_path = datasets_dir / f"{dataset_name}.json"
        
        # Check if file exists
        if not file_path.exists():
            logger.error(f"Benchmark file not found: {file_path}")
            return []
        
        # Load JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract questions
            if isinstance(data, dict):
                questions = data.get('questions', [])
            elif isinstance(data, list):
                questions = data
            else:
                logger.error(f"Invalid JSON format in {file_path}")
                return []
            
            # Limit number of questions if specified
            if num_questions and num_questions > 0:
                questions = questions[:num_questions]
            
            logger.info(f"Loaded {len(questions)} questions from {file_path}")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading questions from {file_path}: {e}")
            return []
    
    def _save_results(
        self,
        results_data: Dict[str, Any],
        dataset_name: str,
        output_dir: str
    ) -> Path:
        """
        Save evaluation results to local JSON file.
        
        Args:
            results_data: Complete results data to save
            dataset_name: Name of benchmark dataset
            output_dir: Output directory
        
        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename with eval_id and dataset name
        filename = f"eval_{self.eval_id}_{dataset_name}.json"
        file_path = output_path / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully saved results to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save results to {file_path}: {e}")
            raise


# Example usage
if __name__ == "__main__":
    async def test_evaluation():
        logging.basicConfig(level=logging.INFO)
        
        orchestrator = EvaluationOrchestrator()
        await orchestrator.initialize()
        
        summary = await orchestrator.run_evaluation(
            dataset_name="factual_questions",
            num_questions=10,
            output_dir="./benchmarks/results"
        )
        
        print("\n=== Evaluation Summary ===")
        print(json.dumps(summary, indent=2))
    
    asyncio.run(test_evaluation())
