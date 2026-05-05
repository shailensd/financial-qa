"""
Unit tests for the Planner node.

Tests the planner_node function's ability to:
- Build prompts with system instructions, memory context, and few-shot examples
- Call LLM and parse JSON responses
- Filter tool calls against firing restrictions
- Handle repair feedback from Critic
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agent.pipeline import planner_node, _load_few_shot_examples


class TestPlannerNode:
    """Test suite for planner_node function."""
    
    def test_planner_basic_lookup_query(self):
        """Test planner generates LOOKUP tool call for simple factual query."""
        state = {
            "query": "What was Apple's revenue in FY2023?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        # Mock LLM response
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Apple",
                    "attribute": "revenue FY2023"
                }
            }
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        assert len(result["plan"]) == 1
        assert result["plan"][0]["tool"] == "LOOKUP"
        assert result["plan"][0]["inputs"]["entity"] == "Apple"
    
    def test_planner_calculate_query(self):
        """Test planner generates CALCULATE tool call for numeric query."""
        state = {
            "query": "What is the revenue growth rate for Meta?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        # Mock LLM response with LOOKUP + CALCULATE
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Meta",
                    "attribute": "revenue 2022"
                }
            },
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Meta",
                    "attribute": "revenue 2023"
                }
            },
            {
                "tool": "CALCULATE",
                "inputs": {
                    "expression": "(revenue_2023 - revenue_2022) / revenue_2022 * 100"
                }
            }
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        assert len(result["plan"]) == 3
        # Verify CALCULATE is included (query has "growth" keyword)
        tool_names = [tc["tool"] for tc in result["plan"]]
        assert "CALCULATE" in tool_names
    
    def test_planner_compare_query(self):
        """Test planner generates COMPARE tool call for comparison query."""
        state = {
            "query": "Compare Netflix's operating margin in Q1 2023 versus Q1 2024.",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        # Mock LLM response
        mock_plan = [
            {
                "tool": "COMPARE",
                "inputs": {
                    "entity1": "Netflix",
                    "period1": "Q1 2023",
                    "entity2": "Netflix",
                    "period2": "Q1 2024"
                }
            }
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        assert len(result["plan"]) == 1
        assert result["plan"][0]["tool"] == "COMPARE"
    
    def test_planner_filters_unavailable_tools(self):
        """Test planner filters out tools that don't meet firing restrictions."""
        state = {
            "query": "What was Apple's CEO in 2023?",  # No numeric keywords
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        # Mock LLM response includes CALCULATE (which shouldn't fire)
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Apple",
                    "attribute": "CEO 2023"
                }
            },
            {
                "tool": "CALCULATE",  # Should be filtered out
                "inputs": {
                    "expression": "1 + 1"
                }
            }
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        # CALCULATE should be filtered out
        assert len(result["plan"]) == 1
        assert result["plan"][0]["tool"] == "LOOKUP"
    
    def test_planner_with_memory_context(self):
        """Test planner includes memory context in prompt."""
        state = {
            "query": "What about their net income?",
            "memory_context": "[Session Summary]\nPrevious query was about Apple's revenue.\n",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Apple",
                    "attribute": "net income"
                }
            }
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
            
            # Verify memory context was included in the prompt
            call_args = mock_router.complete.call_args
            messages = call_args[1]["messages"]
            user_message = messages[1]["content"]
            assert "Session Context" in user_message
            assert "Previous query was about Apple's revenue" in user_message
        
        assert "plan" in result
        assert len(result["plan"]) == 1
    
    def test_planner_with_repair_feedback(self):
        """Test planner incorporates critic feedback for repair."""
        state = {
            "query": "What was Tesla's revenue in 2023?",
            "critic_feedback": "The number $96.8B does not match the cited chunk. Please search for more precise revenue figures.",
            "repair_count": 1,
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Tesla",
                    "attribute": "total revenue fiscal year 2023"
                }
            }
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
            
            # Verify repair feedback was included in the prompt
            call_args = mock_router.complete.call_args
            messages = call_args[1]["messages"]
            user_message = messages[1]["content"]
            assert "Critic Feedback" in user_message
            assert "Repair Iteration 1" in user_message
            assert "does not match the cited chunk" in user_message
        
        assert "plan" in result
    
    def test_planner_handles_markdown_wrapped_json(self):
        """Test planner correctly parses JSON wrapped in markdown code blocks."""
        state = {
            "query": "What was Apple's revenue?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Apple",
                    "attribute": "revenue"
                }
            }
        ]
        
        # LLM returns JSON wrapped in markdown
        markdown_response = f"```json\n{json.dumps(mock_plan)}\n```"
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = markdown_response
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        assert len(result["plan"]) == 1
        assert result["plan"][0]["tool"] == "LOOKUP"
    
    def test_planner_handles_invalid_json(self):
        """Test planner returns empty plan on JSON parse error."""
        state = {
            "query": "What was Apple's revenue?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = "This is not valid JSON"
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        assert result["plan"] == []
    
    def test_planner_handles_non_list_response(self):
        """Test planner returns empty plan if LLM returns non-list."""
        state = {
            "query": "What was Apple's revenue?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        # LLM returns a dict instead of a list
        mock_response = {"tool": "LOOKUP", "inputs": {"entity": "Apple"}}
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_response)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        assert result["plan"] == []
    
    def test_planner_skips_invalid_tool_calls(self):
        """Test planner skips tool calls without required fields."""
        state = {
            "query": "What was Apple's revenue?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        # Mock plan with invalid tool calls
        mock_plan = [
            {
                "tool": "LOOKUP",
                "inputs": {
                    "entity": "Apple",
                    "attribute": "revenue"
                }
            },
            {
                "tool": "CALCULATE"
                # Missing "inputs" field
            },
            "invalid_string_entry"  # Not a dict
        ]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            result = planner_node(state)
        
        assert "plan" in result
        # Only the valid LOOKUP should remain
        assert len(result["plan"]) == 1
        assert result["plan"][0]["tool"] == "LOOKUP"
    
    def test_planner_uses_deterministic_temperature(self):
        """Test planner calls LLM with temperature=0.0 for deterministic planning."""
        state = {
            "query": "What was Apple's revenue?",
            "model_used": "gemini",
            "gemini_api_key": "test_key"
        }
        
        mock_plan = [{"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}]
        
        with patch('app.agent.pipeline.LLMRouter') as mock_router_class:
            mock_router = Mock()
            mock_router.complete.return_value = json.dumps(mock_plan)
            mock_router_class.return_value = mock_router
            
            planner_node(state)
            
            # Verify temperature=0.0 was passed
            call_args = mock_router.complete.call_args
            assert call_args[1]["temperature"] == 0.0


class TestFewShotExamplesLoading:
    """Test suite for few-shot examples loading."""
    
    def test_load_few_shot_examples_filters_planner_only(self):
        """Test that only planner examples are loaded."""
        examples = _load_few_shot_examples()
        
        # All examples should have injection_target="planner"
        for example in examples:
            assert example.get("injection_target") == "planner"
    
    def test_load_few_shot_examples_caches_result(self):
        """Test that few-shot examples are cached after first load."""
        # Load twice
        examples1 = _load_few_shot_examples()
        examples2 = _load_few_shot_examples()
        
        # Should return the same object (cached)
        assert examples1 is examples2
    
    def test_few_shot_examples_have_required_fields(self):
        """Test that few-shot examples have required fields."""
        examples = _load_few_shot_examples()
        
        assert len(examples) > 0, "Should have at least one planner example"
        
        for example in examples:
            assert "id" in example
            assert "injection_target" in example
            assert "query" in example
            assert "expected_plan" in example
            assert isinstance(example["expected_plan"], list)
