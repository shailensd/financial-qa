"""
Integration tests for structured logging in the agent pipeline.

Tests the integration between the agent pipeline and structured logging
to verify that execution traces are properly captured and persisted.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.pipeline import run_agent_pipeline


class TestPipelineLogging:
    """Test suite for pipeline logging integration."""
    
    @pytest.mark.asyncio
    async def test_run_agent_pipeline_logs_execution(self):
        """Test that run_agent_pipeline logs execution to database."""
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        # Mock CRUD operations - patch at the module level where it's imported
        with patch('app.crud.create_query', new_callable=AsyncMock) as mock_create_query, \
             patch('app.crud.create_response', new_callable=AsyncMock) as mock_create_response, \
             patch('app.crud.create_citation', new_callable=AsyncMock) as mock_create_citation:
            
            # Mock query creation
            mock_query = MagicMock(id=42)
            mock_create_query.return_value = mock_query
            
            # Mock response creation
            mock_response = MagicMock(id=100)
            mock_create_response.return_value = mock_response
            
            # Mock structured logger - patch where it's imported
            with patch('app.logging.structured_logger') as mock_logger:
                mock_logger.log_request = AsyncMock()
                
                # Mock the graph execution
                with patch('app.agent.pipeline.build_agent_graph') as mock_build_graph:
                    # Create mock graph
                    mock_graph = AsyncMock()
                    mock_build_graph.return_value = mock_graph
                    
                    # Mock graph invocation result
                    mock_graph.ainvoke = AsyncMock(return_value={
                        "draft_response": "Apple's revenue in FY2023 was $383.3 billion.",
                        "confidence_score": 0.92,
                        "refusal": False,
                        "refusal_reason": None,
                        "citations": [
                            {"chunk_id": 1, "relevance_score": 0.95},
                            {"chunk_id": 2, "relevance_score": 0.88}
                        ],
                        "repair_count": 0,
                        "plan": [
                            {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
                        ],
                        "tool_results": [
                            {"tool": "LOOKUP", "status": "success", "output": {"chunk_text": "Revenue: $383.3B"}}
                        ],
                        "critic_verdict": "approved"
                    })
                    
                    # Run pipeline
                    result = await run_agent_pipeline(
                        query="What was Apple's revenue in FY2023?",
                        session_id="test_session",
                        model_used="gemini",
                        db=mock_db,
                        gemini_api_key="test_key"
                    )
                    
                    # Verify query was created
                    mock_create_query.assert_called_once()
                    assert mock_create_query.call_args.kwargs["session_id"] == "test_session"
                    assert mock_create_query.call_args.kwargs["query_text"] == "What was Apple's revenue in FY2023?"
                    
                    # Verify response was created
                    mock_create_response.assert_called_once()
                    assert mock_create_response.call_args.kwargs["query_id"] == 42
                    assert mock_create_response.call_args.kwargs["confidence_score"] == 0.92
                    
                    # Verify citations were created
                    assert mock_create_citation.call_count == 2
                    
                    # Verify structured logger was called
                    mock_logger.log_request.assert_called_once()
                    log_call_args = mock_logger.log_request.call_args.kwargs
                    assert log_call_args["session_id"] == "test_session"
                    assert log_call_args["query_id"] == 42
                    assert log_call_args["model_used"] == "gemini"
                    assert log_call_args["refusal_decision"] is False
                    assert log_call_args["critic_verdict"] == "approved"
                    assert log_call_args["repair_count"] == 0
                    assert len(log_call_args["chunk_ids"]) == 2
                    
                    # Verify database commit was called
                    mock_db.commit.assert_called_once()
                    
                    # Verify result structure
                    assert result["response_text"] == "Apple's revenue in FY2023 was $383.3 billion."
                    assert result["confidence_score"] == 0.92
                    assert result["refusal_flag"] is False
                    assert len(result["citations"]) == 2
    
    @pytest.mark.asyncio
    async def test_run_agent_pipeline_logs_refusal(self):
        """Test that refusals are properly logged."""
        
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        with patch('app.crud.create_query', new_callable=AsyncMock) as mock_create_query, \
             patch('app.crud.create_response', new_callable=AsyncMock) as mock_create_response, \
             patch('app.crud.create_citation', new_callable=AsyncMock) as mock_create_citation:
            
            mock_query = MagicMock(id=42)
            mock_create_query.return_value = mock_query
            
            mock_response = MagicMock(id=100)
            mock_create_response.return_value = mock_response
            
            with patch('app.logging.structured_logger') as mock_logger:
                mock_logger.log_request = AsyncMock()
                
                with patch('app.agent.pipeline.build_agent_graph') as mock_build_graph:
                    mock_graph = AsyncMock()
                    mock_build_graph.return_value = mock_graph
                    
                    # Mock refusal response
                    mock_graph.ainvoke = AsyncMock(return_value={
                        "draft_response": "",
                        "confidence_score": 0.0,
                        "refusal": True,
                        "refusal_reason": "investment_advice_prohibited",
                        "citations": [],
                        "repair_count": 0,
                        "plan": [],
                        "tool_results": [],
                        "critic_verdict": "n/a"
                    })
                    
                    result = await run_agent_pipeline(
                        query="Should I buy Apple stock?",
                        session_id="test_session",
                        model_used="gemini",
                        db=mock_db,
                        gemini_api_key="test_key"
                    )
                    
                    # Verify refusal was logged
                    mock_logger.log_request.assert_called_once()
                    log_call_args = mock_logger.log_request.call_args.kwargs
                    assert log_call_args["refusal_decision"] is True
                    assert log_call_args["refusal_reason"] == "investment_advice_prohibited"
                    
                    # Verify result
                    assert result["refusal_flag"] is True
                    assert result["refusal_reason"] == "investment_advice_prohibited"
    
    @pytest.mark.asyncio
    async def test_run_agent_pipeline_handles_errors(self):
        """Test that pipeline errors are handled gracefully and logged."""
        
        mock_db = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        with patch('app.agent.pipeline.build_agent_graph') as mock_build_graph:
            # Mock graph to raise an exception
            mock_graph = AsyncMock()
            mock_build_graph.return_value = mock_graph
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution failed"))
            
            result = await run_agent_pipeline(
                query="What is revenue?",
                session_id="test_session",
                model_used="gemini",
                db=mock_db,
                gemini_api_key="test_key"
            )
            
            # Verify error response
            assert "Error: Agent pipeline failed" in result["response_text"]
            assert result["confidence_score"] == 0.0
            assert "error" in result["agent_trace"]
            
            # Verify rollback was called
            mock_db.rollback.assert_called_once()
