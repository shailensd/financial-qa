"""
Unit tests for EvaluationRunner.

Tests the evaluation runner with Ragas integration.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from eval.runner import EvaluationRunner


@pytest.fixture
def mock_db_session_factory():
    """Create a mock database session factory."""
    def factory():
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session
    return factory


@pytest.fixture
def evaluation_runner(mock_db_session_factory, tmp_path):
    """Create an EvaluationRunner instance with a temporary test set."""
    # Create a minimal test set
    test_set = [
        {
            "id": 1,
            "question": "What was Apple's revenue in 2024?",
            "category": "factual_lookup",
            "company": "AAPL",
            "expected_behavior": "ANSWER",
            "expected_answer": "Apple's revenue was $383 billion.",
            "difficulty": "easy"
        },
        {
            "id": 2,
            "question": "Should I buy Apple stock?",
            "category": "refusal_investment_advice",
            "company": "AAPL",
            "expected_behavior": "REFUSE",
            "difficulty": "easy"
        }
    ]
    
    # Write test set to temporary file
    test_set_path = tmp_path / "test_evaluation_set.json"
    with open(test_set_path, 'w') as f:
        json.dump(test_set, f)
    
    return EvaluationRunner(
        db_session_factory=mock_db_session_factory,
        eval_set_path=str(test_set_path)
    )


def test_load_test_cases(evaluation_runner):
    """Test that test cases are loaded correctly."""
    assert len(evaluation_runner.test_cases) == 2
    assert evaluation_runner.test_cases[0]['id'] == 1
    assert evaluation_runner.test_cases[1]['expected_behavior'] == 'REFUSE'


@pytest.mark.asyncio
async def test_run_evaluation_empty_test_set(mock_db_session_factory):
    """Test evaluation with empty test set."""
    runner = EvaluationRunner(
        db_session_factory=mock_db_session_factory,
        eval_set_path="/nonexistent/path.json"
    )
    
    result = await runner.run(model="gemini")
    
    assert result['faithfulness'] == 0.0
    assert result['answer_relevancy'] == 0.0
    assert result['refusal_accuracy'] == 0.0
    assert result['test_cases_run'] == 0


@pytest.mark.asyncio
async def test_aggregate_method(evaluation_runner):
    """Test the aggregate method."""
    # Mock the crud.get_evaluation_aggregates function
    with patch('eval.runner.crud.get_evaluation_aggregates') as mock_get_agg:
        # Create mock aggregate objects
        mock_agg = MagicMock()
        mock_agg.model_used = "gemini"
        mock_agg.mean_faithfulness = 0.85
        mock_agg.mean_answer_relevancy = 0.90
        mock_agg.test_cases_count = 10
        mock_agg.refusal_accuracy = 1.0
        mock_agg.created_at.isoformat.return_value = "2025-01-02T00:00:00"
        
        # Make the mock return a coroutine
        async def mock_get_agg_coro(*args, **kwargs):
            return [mock_agg]
        
        mock_get_agg.side_effect = mock_get_agg_coro
        
        result = await evaluation_runner.aggregate(model="gemini")
        
        assert len(result['aggregates']) == 1
        assert result['aggregates'][0]['model'] == "gemini"
        assert result['aggregates'][0]['mean_faithfulness'] == 0.85
        assert result['aggregates'][0]['mean_answer_relevancy'] == 0.90
        assert result['aggregates'][0]['refusal_accuracy'] == 1.0


def test_evaluation_runner_initialization(mock_db_session_factory):
    """Test EvaluationRunner initialization with default path."""
    runner = EvaluationRunner(db_session_factory=mock_db_session_factory)
    
    # Should default to evaluation_set_seed.json
    assert runner.eval_set_path.endswith('evaluation_set_seed.json')
