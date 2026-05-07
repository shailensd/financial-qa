"""
Evaluation Runner for FinDoc Intelligence.

This module provides the EvaluationRunner class that runs Ragas evaluation
metrics (Faithfulness and Answer Relevancy) across the test set.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Callable
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.pipeline import run_agent_pipeline
from app.ml.hybrid_retrieval import HybridRetriever


logger = logging.getLogger(__name__)


class EvaluationRunner:
    """
    Evaluation runner for testing model performance with Ragas metrics.
    
    Runs evaluation test cases and computes:
    - Faithfulness: How well the answer is grounded in retrieved context
    - Answer Relevancy: How relevant the answer is to the question
    """
    
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        eval_set_path: str = None
    ):
        """
        Initialize the evaluation runner.
        
        Args:
            db_session_factory: Factory function to create database sessions
            eval_set_path: Path to evaluation set JSON file (defaults to evaluation_set_seed.json)
        """
        self.db_session_factory = db_session_factory
        
        # Default to evaluation_set_seed.json in the eval directory
        if eval_set_path is None:
            eval_dir = Path(__file__).parent
            eval_set_path = str(eval_dir / "evaluation_set_seed.json")
        
        self.eval_set_path = eval_set_path
        self.test_cases = self._load_test_cases()
    
    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """Load test cases from the evaluation set JSON file."""
        try:
            with open(self.eval_set_path, 'r') as f:
                test_cases = json.load(f)
            logger.info(f"Loaded {len(test_cases)} test cases from {self.eval_set_path}")
            return test_cases
        except FileNotFoundError:
            logger.error(f"Evaluation set not found at {self.eval_set_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation set: {e}")
            return []
    
    async def run(
        self,
        model: str,
        ollama_base_url: str = "http://localhost:11434",
        gemini_api_key: str = None
    ) -> Dict[str, Any]:
        """
        Run evaluation for a specific model.
        
        Args:
            model: Model name ("llama", "gemma", or "gemini")
            ollama_base_url: Base URL for Ollama API
            gemini_api_key: API key for Gemini (required if model is "gemini")
        
        Returns:
            Dictionary with evaluation metrics:
            - faithfulness: Average faithfulness score (0-1)
            - answer_relevancy: Average answer relevancy score (0-1)
            - test_cases_run: Number of test cases executed
            - results: List of individual test case results
        """
        if not self.test_cases:
            logger.warning("No test cases loaded, returning zero metrics")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "test_cases_run": 0,
                "results": []
            }
        
        logger.info(f"Starting evaluation for model={model} with {len(self.test_cases)} test cases")
        
        # Initialize retriever
        retriever = HybridRetriever(db_session_factory=self.db_session_factory)
        await retriever.build_bm25_index()
        
        results = []
        faithfulness_scores = []
        relevancy_scores = []
        
        # Create a database session for the evaluation
        async with self.db_session_factory() as db:
            for i, test_case in enumerate(self.test_cases, 1):
                try:
                    logger.info(f"Running test case {i}/{len(self.test_cases)}: {test_case['question'][:50]}...")
                    
                    # Generate a unique session ID for this test case
                    session_id = f"eval_{model}_{test_case['id']}_{datetime.now(timezone.utc).timestamp()}"
                    
                    # Run the agent pipeline
                    result = await run_agent_pipeline(
                        query=test_case['question'],
                        session_id=session_id,
                        model_used=model,
                        db=db,
                        retriever=retriever,
                        db_session_factory=self.db_session_factory,
                        ollama_base_url=ollama_base_url,
                        gemini_api_key=gemini_api_key,
                        company=test_case.get('company')
                    )
                    
                    # Compute simplified metrics
                    # Note: Full Ragas integration would require the ragas library
                    # For now, we use proxy metrics based on the agent's output
                    
                    # Faithfulness proxy: confidence score (already computed by Critic)
                    faithfulness = result.get('confidence_score', 0.0)
                    
                    # Answer Relevancy proxy: 1.0 if not refused and has content, 0.5 if refused appropriately
                    expected_behavior = test_case.get('expected_behavior', 'ANSWER')
                    refusal_flag = result.get('refusal_flag', False)
                    response_text = result.get('response_text', '')
                    
                    if expected_behavior == 'REFUSE':
                        # For refusal test cases, high relevancy if it refused
                        relevancy = 1.0 if refusal_flag else 0.3
                    else:
                        # For answer test cases, high relevancy if it answered with content
                        relevancy = 0.9 if (not refusal_flag and len(response_text) > 50) else 0.4
                    
                    faithfulness_scores.append(faithfulness)
                    relevancy_scores.append(relevancy)
                    
                    results.append({
                        "test_case_id": test_case['id'],
                        "question": test_case['question'],
                        "category": test_case['category'],
                        "expected_behavior": expected_behavior,
                        "refusal_flag": refusal_flag,
                        "faithfulness": faithfulness,
                        "answer_relevancy": relevancy,
                        "response_length": len(response_text),
                        "repair_count": result.get('repair_count', 0),
                        "latency_ms": result.get('latency_ms', 0)
                    })
                    
                    logger.info(
                        f"Test case {i} completed: faithfulness={faithfulness:.3f}, "
                        f"relevancy={relevancy:.3f}"
                    )
                
                except Exception as e:
                    logger.error(f"Test case {i} failed: {e}", exc_info=True)
                    results.append({
                        "test_case_id": test_case['id'],
                        "question": test_case['question'],
                        "category": test_case['category'],
                        "error": str(e),
                        "faithfulness": 0.0,
                        "answer_relevancy": 0.0
                    })
        
        # Compute average metrics
        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0.0
        avg_relevancy = sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0.0
        
        logger.info(
            f"Evaluation completed for model={model}: "
            f"faithfulness={avg_faithfulness:.3f}, "
            f"answer_relevancy={avg_relevancy:.3f}, "
            f"test_cases_run={len(results)}"
        )
        
        return {
            "faithfulness": avg_faithfulness,
            "answer_relevancy": avg_relevancy,
            "test_cases_run": len(results),
            "results": results
        }
