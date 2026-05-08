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
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.agent.pipeline import run_agent_pipeline
from app.ml.hybrid_retrieval import HybridRetriever
from app import crud


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
            - refusal_accuracy: Accuracy of refusal decisions (0-1)
            - test_cases_run: Number of test cases executed
            - results: List of individual test case results
        """
        if not self.test_cases:
            logger.warning("No test cases loaded, returning zero metrics")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "refusal_accuracy": 0.0,
                "test_cases_run": 0,
                "results": []
            }
        
        logger.info(f"Starting evaluation for model={model} with {len(self.test_cases)} test cases")
        
        # Initialize retriever
        retriever = HybridRetriever(db_session_factory=self.db_session_factory)
        await retriever.build_bm25_index()
        
        results = []
        
        # Prepare data for Ragas evaluation
        ragas_data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
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
                    
                    # Extract response data
                    response_text = result.get('response_text', '')
                    refusal_flag = result.get('refusal_flag', False)
                    expected_behavior = test_case.get('expected_behavior', 'ANSWER')
                    expected_refusal = (expected_behavior == 'REFUSE')
                    
                    # Verify refusal test cases
                    refusal_correct = (refusal_flag == expected_refusal)
                    
                    # Extract contexts from citations for Ragas
                    citations = result.get('citations', [])
                    contexts = [citation.get('chunk_text', '') for citation in citations if citation.get('chunk_text')]
                    
                    # If no contexts available, use empty list (Ragas will handle it)
                    if not contexts:
                        contexts = [""]
                    
                    # For refusal cases, we still need to provide data to Ragas
                    # but the metrics will be low (which is expected)
                    if not refusal_flag:
                        # Only add to Ragas evaluation if not refused
                        ragas_data["question"].append(test_case['question'])
                        ragas_data["answer"].append(response_text)
                        ragas_data["contexts"].append(contexts)
                        # Use expected_answer as ground truth if available, otherwise use empty string
                        ragas_data["ground_truth"].append(test_case.get('expected_answer', ''))
                    
                    # Store preliminary result (will update with Ragas scores later)
                    results.append({
                        "test_case_id": str(test_case['id']),
                        "question": test_case['question'],
                        "category": test_case['category'],
                        "expected_behavior": expected_behavior,
                        "refusal_flag": refusal_flag,
                        "expected_refusal": expected_refusal,
                        "refusal_correct": refusal_correct,
                        "response_text": response_text,
                        "contexts": contexts,
                        "faithfulness": 0.0,  # Will be updated
                        "answer_relevancy": 0.0,  # Will be updated
                        "response_length": len(response_text),
                        "repair_count": result.get('repair_count', 0),
                        "latency_ms": result.get('latency_ms', 0)
                    })
                    
                    logger.info(
                        f"Test case {i} completed: refusal_flag={refusal_flag}, "
                        f"expected_refusal={expected_refusal}, refusal_correct={refusal_correct}"
                    )
                
                except Exception as e:
                    logger.error(f"Test case {i} failed: {e}", exc_info=True)
                    results.append({
                        "test_case_id": str(test_case['id']),
                        "question": test_case['question'],
                        "category": test_case['category'],
                        "expected_behavior": test_case.get('expected_behavior', 'ANSWER'),
                        "refusal_flag": False,
                        "expected_refusal": (test_case.get('expected_behavior', 'ANSWER') == 'REFUSE'),
                        "refusal_correct": False,
                        "response_text": "",
                        "contexts": [],
                        "error": str(e),
                        "faithfulness": 0.0,
                        "answer_relevancy": 0.0,
                        "latency_ms": 0
                    })
        
        # Compute Ragas metrics for non-refused cases
        if ragas_data["question"]:
            try:
                logger.info(f"Computing Ragas metrics for {len(ragas_data['question'])} non-refused cases")
                
                # Create Ragas dataset
                ragas_dataset = Dataset.from_dict(ragas_data)
                
                # Initialize LLM and embeddings for Ragas
                # Use Gemini for evaluation (or the model being tested)
                eval_llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=gemini_api_key
                )
                eval_embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                
                # Evaluate with Ragas
                ragas_results = evaluate(
                    ragas_dataset,
                    metrics=[faithfulness, answer_relevancy],
                    llm=eval_llm,
                    embeddings=eval_embeddings
                )
                
                # Convert to DataFrame to extract row-level scores
                df = ragas_results.to_pandas()
                faithfulness_scores = df['faithfulness'].tolist()
                relevancy_scores = df['answer_relevancy'].tolist()
                
                # Update results with Ragas scores
                non_refused_idx = 0
                for result in results:
                    if not result['refusal_flag'] and 'error' not in result:
                        if non_refused_idx < len(faithfulness_scores):
                            result['faithfulness'] = float(faithfulness_scores[non_refused_idx])
                            result['answer_relevancy'] = float(relevancy_scores[non_refused_idx])
                            non_refused_idx += 1
                
                logger.info("Ragas metrics computed successfully")
            
            except Exception as e:
                logger.error(f"Failed to compute Ragas metrics: {e}", exc_info=True)
                # Continue with zero scores for Ragas metrics
        
        # Compute aggregate metrics
        faithfulness_scores = [r['faithfulness'] for r in results if not r['refusal_flag'] and 'error' not in r]
        relevancy_scores = [r['answer_relevancy'] for r in results if not r['refusal_flag'] and 'error' not in r]
        refusal_correct_count = sum(1 for r in results if r['refusal_correct'])
        
        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0.0
        avg_relevancy = sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0.0
        refusal_accuracy = refusal_correct_count / len(results) if results else 0.0
        
        logger.info(
            f"Evaluation completed for model={model}: "
            f"faithfulness={avg_faithfulness:.3f}, "
            f"answer_relevancy={avg_relevancy:.3f}, "
            f"refusal_accuracy={refusal_accuracy:.3f}, "
            f"test_cases_run={len(results)}"
        )
        
        # Persist results to database
        async with self.db_session_factory() as db:
            # Persist per-case results
            for result in results:
                if 'error' not in result:
                    await crud.create_evaluation_result(
                        db=db,
                        test_case_id=result['test_case_id'],
                        model_used=model,
                        query_text=result['question'],
                        response_text=result['response_text'],
                        faithfulness=result['faithfulness'],
                        answer_relevancy=result['answer_relevancy'],
                        refusal_flag=result['refusal_flag'],
                        expected_refusal=result['expected_refusal'],
                        latency_ms=result['latency_ms']
                    )
            
            # Persist aggregate results
            await crud.create_evaluation_aggregate(
                db=db,
                model_used=model,
                mean_faithfulness=avg_faithfulness,
                mean_answer_relevancy=avg_relevancy,
                test_cases_count=len(results),
                refusal_accuracy=refusal_accuracy
            )
            
            await db.commit()
            logger.info("Evaluation results persisted to database")
        
        return {
            "faithfulness": avg_faithfulness,
            "answer_relevancy": avg_relevancy,
            "refusal_accuracy": refusal_accuracy,
            "test_cases_run": len(results),
            "results": results
        }
    
    async def aggregate(self, model: str = None) -> Dict[str, Any]:
        """
        Retrieve aggregate evaluation metrics from the database.
        
        Args:
            model: Optional model name to filter by. If None, returns aggregates for all models.
        
        Returns:
            Dictionary with aggregate metrics per model:
            - aggregates: List of aggregate records with model, faithfulness, answer_relevancy, etc.
        """
        async with self.db_session_factory() as db:
            aggregates = await crud.get_evaluation_aggregates(db=db, model_used=model)
            
            return {
                "aggregates": [
                    {
                        "model": agg.model_used,
                        "mean_faithfulness": agg.mean_faithfulness,
                        "mean_answer_relevancy": agg.mean_answer_relevancy,
                        "test_cases_count": agg.test_cases_count,
                        "refusal_accuracy": agg.refusal_accuracy,
                        "created_at": agg.created_at.isoformat()
                    }
                    for agg in aggregates
                ]
            }
