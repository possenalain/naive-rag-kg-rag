"""
LLM-based scoring for RAG evaluation.
Evaluates answers across 5 dimensions using an LLM as judge.
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
import json

from src.utils.llm import LLMFactory, LLMProvider
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMScorer:
    """
    Scores RAG answers using LLM as a judge.
    
    Evaluation Dimensions (1-5 scale):
    1. Correctness: How factually accurate is the answer?
    2. Completeness: How thoroughly does it address the question?
    3. Relevance: How well does it stay on topic?
    4. Faithfulness: How well does it stick to the provided context?
    5. Clarity: How clear and well-structured is the answer?
    """
    
    def __init__(self):
        self.llm = None
    
    async def initialize(self):
        """Initialize LLM for scoring."""
        if self.llm is None:
            self.llm = LLMFactory.create_llm_provider(
                provider=settings.evaluation.llm_provider,
                model_name=settings.evaluation.llm_model,
                api_key=settings.evaluation.llm_api_key
            )
            logger.info("LLM Scorer initialized")
    
    def _create_scoring_prompt(
        self,
        question: str,
        ground_truth: str,
        generated_answer: str,
        retrieved_context: str
    ) -> str:
        """Create prompt for LLM-based scoring."""
        prompt = f"""You are an expert evaluator assessing the quality of AI-generated answers. 

Evaluate the GENERATED ANSWER across 5 dimensions on a scale of 1-5:

QUESTION:
{question}

GROUND TRUTH ANSWER:
{ground_truth}

RETRIEVED CONTEXT:
{retrieved_context}

GENERATED ANSWER:
{generated_answer}

EVALUATION DIMENSIONS:
1. **Correctness** (1-5): How factually accurate is the answer compared to the ground truth?
   - 5: Completely correct, matches ground truth
   - 3: Mostly correct with minor errors
   - 1: Incorrect or contradicts ground truth

2. **Completeness** (1-5): How thoroughly does it address all aspects of the question?
   - 5: Addresses all aspects comprehensively
   - 3: Addresses main points but misses some details
   - 1: Incomplete, misses major points

3. **Relevance** (1-5): How well does it stay focused on the question?
   - 5: Perfectly relevant, no tangents
   - 3: Mostly relevant with some off-topic content
   - 1: Off-topic or irrelevant

4. **Faithfulness** (1-5): How well does it adhere to the retrieved context without hallucination?
   - 5: Fully grounded in context, no hallucinations
   - 3: Mostly faithful with minor unsupported claims
   - 1: Significant hallucinations or contradicts context

5. **Clarity** (1-5): How clear, coherent, and well-structured is the answer?
   - 5: Excellently written, very clear
   - 3: Understandable but could be clearer
   - 1: Confusing or poorly structured

Provide your evaluation in JSON format:
{{
  "correctness": <score>,
  "correctness_explanation": "<brief explanation>",
  "completeness": <score>,
  "completeness_explanation": "<brief explanation>",
  "relevance": <score>,
  "relevance_explanation": "<brief explanation>",
  "faithfulness": <score>,
  "faithfulness_explanation": "<brief explanation>",
  "clarity": <score>,
  "clarity_explanation": "<brief explanation>",
  "overall_assessment": "<1-2 sentence summary>"
}}

IMPORTANT: Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    async def score_answer(
        self,
        question: str,
        ground_truth: str,
        generated_answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Score a single answer across all dimensions.
        
        Args:
            question: The question asked
            ground_truth: Reference answer
            generated_answer: RAG-generated answer
            retrieved_chunks: Context chunks used
        
        Returns:
            Dictionary with scores and explanations
        """
        if not self.llm:
            await self.initialize()
        
        # Format retrieved context
        context_parts = [chunk.get('chunk_text', '') for chunk in retrieved_chunks]
        retrieved_context = "\n\n".join(context_parts[:5])  # Limit to 5 chunks
        
        # Create scoring prompt
        prompt = self._create_scoring_prompt(
            question=question,
            ground_truth=ground_truth,
            generated_answer=generated_answer,
            retrieved_context=retrieved_context
        )
        
        # Generate score with retries
        max_retries = settings.evaluation.max_retries
        for attempt in range(max_retries):
            try:
                logger.debug(f"Scoring attempt {attempt + 1}/{max_retries}")
                
                response = await self.llm.generate(
                    prompt=prompt,
                    temperature=settings.evaluation.temperature,
                    max_tokens=1024
                )
                
                # Parse JSON response
                # Extract JSON from response (handle markdown code blocks)
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
                
                scores = json.loads(response.strip())
                
                # Validate scores
                required_keys = ['correctness', 'completeness', 'relevance', 'faithfulness', 'clarity']
                if all(k in scores for k in required_keys):
                    logger.info("Successfully scored answer")
                    return scores
                else:
                    logger.warning(f"Missing keys in response: {scores.keys()}")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(settings.evaluation.retry_delay)
                    continue
                    
            except Exception as e:
                logger.error(f"Scoring error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(settings.evaluation.retry_delay)
                    continue
        
        # Fallback: return default scores
        logger.error("Failed to score answer after retries, using defaults")
        return {
            'correctness': 0,
            'completeness': 0,
            'relevance': 0,
            'faithfulness': 0,
            'clarity': 0,
            'correctness_explanation': 'Scoring failed',
            'completeness_explanation': 'Scoring failed',
            'relevance_explanation': 'Scoring failed',
            'faithfulness_explanation': 'Scoring failed',
            'clarity_explanation': 'Scoring failed',
            'overall_assessment': 'Scoring failed'
        }
    
    async def batch_score(
        self,
        evaluations: List[Dict[str, Any]],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Score multiple answers in batches.
        
        Args:
            evaluations: List of evaluation dicts with question, ground_truth, generated_answer, retrieved_chunks
            batch_size: Number of concurrent scoring operations
        
        Returns:
            List of scores
        """
        scores = []
        
        for i in range(0, len(evaluations), batch_size):
            batch = evaluations[i:i + batch_size]
            logger.info(f"Scoring batch {i // batch_size + 1} ({len(batch)} items)")
            
            tasks = [
                self.score_answer(
                    question=eval_item['question'],
                    ground_truth=eval_item['ground_truth'],
                    generated_answer=eval_item['generated_answer'],
                    retrieved_chunks=eval_item['retrieved_chunks']
                )
                for eval_item in batch
            ]
            
            batch_scores = await asyncio.gather(*tasks)
            scores.extend(batch_scores)
        
        return scores


# Example usage
if __name__ == "__main__":
    async def test_scorer():
        logging.basicConfig(level=logging.INFO)
        
        scorer = LLMScorer()
        await scorer.initialize()
        
        scores = await scorer.score_answer(
            question="What is the capital of France?",
            ground_truth="The capital of France is Paris.",
            generated_answer="Paris is the capital of France. It is known for the Eiffel Tower.",
            retrieved_chunks=[
                {'chunk_text': "Paris is the capital and largest city of France."}
            ]
        )
        
        print("\nScores:")
        for key, value in scores.items():
            print(f"{key}: {value}")
    
    asyncio.run(test_scorer())
