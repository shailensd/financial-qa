"""
Unit tests for the Executor node.

Tests cover:
- Tool execution iteration
- Tool result collection
- Draft response generation
- Citation population
- Error handling (continue on tool failure)
- Structured logging
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.agent.pipeline import executor_node
from app.ml.hybrid_retrieval import ScoredChunk
import app.agent.pipeline


class TestExecutorNode:
    """Test executor_node function."""
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_executes_all_tools_in_plan(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should iterate through plan and execute each tool."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        # Setup mocks
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response text"
        mock_llm_router_class.return_value = mock_llm_router
        
        # Mock tool execution results
        mock_execute_tool.side_effect = [
            {"chunk_text": "Apple revenue was $383.3B", "chunk_id": 42},
            {"result": 383.3}
        ]
        
        # State with plan
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}},
                {"tool": "CALCULATE", "inputs": {"expression": "383.3"}}
            ],
            "query": "What is Apple's revenue?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        result = executor_node(state)
        
        # Verify all tools were executed
        assert mock_execute_tool.call_count == 2
        assert len(result["tool_results"]) == 2
        
        # Verify tool results structure
        assert result["tool_results"][0]["tool"] == "LOOKUP"
        assert result["tool_results"][0]["status"] == "success"
        assert result["tool_results"][1]["tool"] == "CALCULATE"
        assert result["tool_results"][1]["status"] == "success"
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_collects_tool_results(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should collect all tool results into state."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Test chunk",
            "chunk_id": 123
        }
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        assert "tool_results" in result
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["output"]["chunk_id"] == 123
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_generates_draft_response(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should generate draft response using LLM."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        expected_response = "Apple's revenue in FY2023 was $383.3 billion."
        mock_llm_router.complete.return_value = expected_response
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Apple revenue was $383.3B",
            "chunk_id": 42
        }
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "What is Apple's revenue?",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        assert "draft_response" in result
        assert result["draft_response"] == expected_response
        
        # Verify LLM was called with appropriate prompt
        mock_llm_router.complete.assert_called_once()
        call_args = mock_llm_router.complete.call_args
        assert call_args[1]["model"] == "gemini"
        assert call_args[1]["temperature"] == 0.3
        
        # Verify messages contain query and tool results
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "What is Apple's revenue?" in messages[1]["content"]
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_populates_citations_from_lookup(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should populate citations from LOOKUP tool chunk_ids."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Test chunk",
            "chunk_id": 42
        }
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        assert "citations" in result
        assert len(result["citations"]) == 1
        assert result["citations"][0]["chunk_id"] == 42
        assert "relevance_score" in result["citations"][0]
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_populates_citations_from_compare(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should populate citations from COMPARE tool chunk_ids."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "comparison_result": {
                "entity1": {
                    "chunk_text": "Apple FY2023 revenue $383.3B",
                    "chunk_id": 42,
                    "value": 383.3
                },
                "entity2": {
                    "chunk_text": "Apple FY2022 revenue $365.8B",
                    "chunk_id": 87,
                    "value": 365.8
                },
                "delta": 17.5
            }
        }
        
        state = {
            "plan": [
                {"tool": "COMPARE", "inputs": {
                    "entity1": "Apple", "period1": "FY2023",
                    "entity2": "Apple", "period2": "FY2022"
                }}
            ],
            "query": "Compare Apple revenue",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        assert "citations" in result
        assert len(result["citations"]) == 2
        chunk_ids = [c["chunk_id"] for c in result["citations"]]
        assert 42 in chunk_ids
        assert 87 in chunk_ids
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_continues_on_tool_error(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should log error and continue with remaining tools on tool failure."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        # First tool fails, second succeeds
        mock_execute_tool.side_effect = [
            ValueError("Tool execution failed"),
            {"chunk_text": "Success", "chunk_id": 42}
        ]
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Unknown", "attribute": "revenue"}},
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        # Both tools should be in results
        assert len(result["tool_results"]) == 2
        
        # First tool should have error status
        assert result["tool_results"][0]["status"] == "error"
        assert "error" in result["tool_results"][0]
        
        # Second tool should have success status
        assert result["tool_results"][1]["status"] == "success"
        assert result["tool_results"][1]["output"]["chunk_id"] == 42
        
        # Draft response should still be generated
        assert result["draft_response"] == "Draft response"
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_handles_empty_plan(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should handle empty plan gracefully."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response with no tools"
        mock_llm_router_class.return_value = mock_llm_router
        
        state = {
            "plan": [],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        assert result["tool_results"] == []
        assert result["citations"] == []
        assert result["draft_response"] == "Draft response with no tools"
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_handles_llm_error(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should handle LLM error gracefully."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.side_effect = Exception("LLM API error")
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Test chunk",
            "chunk_id": 42
        }
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        # Tool results should still be collected
        assert len(result["tool_results"]) == 1
        
        # Draft response should contain error message
        assert "Error" in result["draft_response"]
        assert "LLM error" in result["draft_response"]
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_includes_chunk_texts_in_prompt(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should include retrieved chunk texts in generation prompt."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Apple's revenue in FY2023 was $383.3 billion.",
            "chunk_id": 42
        }
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "What is Apple's revenue?",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        # Verify LLM prompt includes chunk text
        call_args = mock_llm_router.complete.call_args
        messages = call_args[1]["messages"]
        user_message = messages[1]["content"]
        
        assert "Apple's revenue in FY2023 was $383.3 billion." in user_message
        assert "Source Documents:" in user_message or "Source Chunk:" in user_message
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_includes_tool_results_in_prompt(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should include tool results in generation prompt."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {"result": 383.3}
        
        state = {
            "plan": [
                {"tool": "CALCULATE", "inputs": {"expression": "383.3"}}
            ],
            "query": "Calculate revenue",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        # Verify LLM prompt includes tool results
        call_args = mock_llm_router.complete.call_args
        messages = call_args[1]["messages"]
        user_message = messages[1]["content"]
        
        assert "Tool Results:" in user_message
        assert "CALCULATE" in user_message
        assert "383.3" in user_message
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_uses_correct_model(
        self, mock_llm_router_class, mock_execute_tool
    ):
        """Executor should use the model specified in state."""
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Test",
            "chunk_id": 1
        }
        
        # Test with different models
        for model in ["llama", "gemma", "gemini"]:
            state = {
                "plan": [
                    {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
                ],
                "query": "Test query",
                "model_used": model
            }
            
            result = executor_node(state)
            
            # Verify correct model was used
            call_args = mock_llm_router.complete.call_args
            assert call_args[1]["model"] == model
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_logs_tool_executions(
        self, mock_llm_router_class, mock_execute_tool, caplog
    ):
        """Executor should log each tool execution."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.return_value = {
            "chunk_text": "Test",
            "chunk_id": 42
        }
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        # Verify logging occurred
        assert "Tool executed successfully: LOOKUP" in caplog.text
    
    @patch('app.agent.tools.execute_tool')
    @patch('app.agent.pipeline.LLMRouter')
    def test_executor_logs_tool_errors(
        self, mock_llm_router_class, mock_execute_tool, caplog
    ):
        """Executor should log tool execution errors."""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Setup mock retriever in global scope
        mock_retriever = Mock()
        app.agent.pipeline._current_retriever = mock_retriever
        
        mock_llm_router = Mock()
        mock_llm_router.complete.return_value = "Draft response"
        mock_llm_router_class.return_value = mock_llm_router
        
        mock_execute_tool.side_effect = ValueError("Tool failed")
        
        state = {
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Unknown", "attribute": "revenue"}}
            ],
            "query": "Test query",
            "model_used": "gemini"
        }
        
        result = executor_node(state)
        
        # Verify error logging occurred
        assert "Tool execution failed: LOOKUP" in caplog.text
        assert "Tool failed" in caplog.text
