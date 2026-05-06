"""
Property-based tests for the repair loop in the agent pipeline.

Tests verify that repair_count never exceeds max_repair_iterations (2)
regardless of how many times the Critic returns repair verdicts.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch

from app.agent.pipeline import (
    AgentState,
    critic_node,
    route_after_critic,
)


class TestRepairLoopBound:
    """Property-based tests for repair loop iteration bounds."""
    
    @given(
        repair_count=st.integers(min_value=0, max_value=10),
        has_numerical_mismatch=st.booleans(),
        has_missing_citations=st.booleans()
    )
    @settings(max_examples=100)
    def test_critic_never_exceeds_max_repair_iterations(
        self,
        repair_count: int,
        has_numerical_mismatch: bool,
        has_missing_citations: bool
    ):
        """
        Property: For any repair_count and validation failures, the Critic
        must never allow repair_count to exceed max_repair_iterations (2).
        
        When repair_count >= 2, the Critic MUST return "approved" verdict
        regardless of validation failures.
        """
        # Build state with varying repair counts and validation failures
        state: AgentState = {
            "repair_count": repair_count,
            "draft_response": "",
            "citations": [],
            "tool_results": []
        }
        
        # Simulate numerical mismatch by adding a number not in chunks
        if has_numerical_mismatch:
            state["draft_response"] = "The revenue was $999.99 billion."
            state["tool_results"] = [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Revenue was $100 million.",
                        "chunk_id": 1
                    }
                }
            ]
        
        # Simulate missing citations by having content but no citations
        if has_missing_citations:
            state["draft_response"] = "This is a factual claim without citations."
            state["citations"] = []
            state["tool_results"] = []
        
        # If neither validation failure, provide valid state
        if not has_numerical_mismatch and not has_missing_citations:
            state["draft_response"] = "The revenue was $100 million."
            state["citations"] = [{"chunk_id": 1, "relevance_score": 0.9}]
            state["tool_results"] = [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Revenue was $100 million.",
                        "chunk_id": 1
                    }
                }
            ]
        
        # Call critic_node
        result = critic_node(state)
        
        # Extract verdict and updated repair_count
        critic_verdict = result.get("critic_verdict")
        # If repair_count is not in result, it means it wasn't incremented
        updated_repair_count = result.get("repair_count", repair_count)
        
        # PROPERTY 1: repair_count must never be incremented beyond 2
        # Only check if repair_count was actually returned (meaning it was incremented)
        if "repair_count" in result:
            assert updated_repair_count <= 2, (
                f"repair_count exceeded max_repair_iterations: "
                f"updated_repair_count={updated_repair_count}"
            )
        
        # PROPERTY 2: When repair_count >= 2, Critic MUST approve
        if repair_count >= 2:
            assert critic_verdict == "approved", (
                f"Critic must approve when repair_count >= 2, "
                f"but got verdict={critic_verdict} for repair_count={repair_count}"
            )
            
            # Confidence score should be low (0.3) when forced approval
            confidence_score = result.get("confidence_score", 1.0)
            assert confidence_score == 0.3, (
                f"Forced approval should have confidence_score=0.3, "
                f"but got {confidence_score}"
            )
        
        # PROPERTY 3: When repair_count < 2 and validation fails, increment count
        if repair_count < 2 and (has_numerical_mismatch or has_missing_citations):
            # Critic should request repair
            assert critic_verdict in ["repair_numerical", "repair_citation"], (
                f"Critic should request repair for validation failures when "
                f"repair_count < 2, but got verdict={critic_verdict}"
            )
            
            # repair_count should be incremented
            assert updated_repair_count == repair_count + 1, (
                f"repair_count should be incremented on repair verdict, "
                f"but got {updated_repair_count} (expected {repair_count + 1})"
            )
    
    @given(
        repair_count=st.integers(min_value=0, max_value=10),
        critic_verdict=st.sampled_from(["approved", "repair_numerical", "repair_citation"])
    )
    @settings(max_examples=50)
    def test_route_after_critic_respects_max_iterations(
        self,
        repair_count: int,
        critic_verdict: str
    ):
        """
        Property: The route_after_critic function must never route back to
        planner when repair_count >= 2, regardless of critic_verdict.
        """
        state: AgentState = {
            "repair_count": repair_count,
            "critic_verdict": critic_verdict
        }
        
        route = route_after_critic(state)
        
        # PROPERTY: When repair_count >= 2, must route to memory_write
        if repair_count >= 2:
            assert route == "memory_write", (
                f"route_after_critic must route to memory_write when "
                f"repair_count >= 2, but got route={route} for "
                f"repair_count={repair_count}, verdict={critic_verdict}"
            )
        
        # PROPERTY: When repair_count < 2 and needs repair, route to planner
        if repair_count < 2 and critic_verdict in ["repair_numerical", "repair_citation"]:
            assert route == "planner", (
                f"route_after_critic should route to planner for repair when "
                f"repair_count < 2 and verdict is repair, but got route={route}"
            )
        
        # PROPERTY: When approved, always route to memory_write
        if critic_verdict == "approved":
            assert route == "memory_write", (
                f"route_after_critic must route to memory_write when approved, "
                f"but got route={route}"
            )
    
    def test_repair_loop_terminates_after_two_iterations(self):
        """
        Integration test: Verify that a repair loop terminates after exactly
        2 iterations even if validation continues to fail.
        """
        # Simulate a state that will always fail validation
        # (number not in chunks)
        state: AgentState = {
            "repair_count": 0,
            "draft_response": "The revenue was $999.99 billion.",
            "citations": [{"chunk_id": 1, "relevance_score": 0.9}],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Revenue was $100 million.",
                        "chunk_id": 1
                    }
                }
            ]
        }
        
        # First iteration: repair_count = 0
        result1 = critic_node(state)
        assert result1["critic_verdict"] == "repair_numerical"
        assert result1["repair_count"] == 1
        
        # Update state with repair_count = 1
        state["repair_count"] = 1
        
        # Second iteration: repair_count = 1
        result2 = critic_node(state)
        assert result2["critic_verdict"] == "repair_numerical"
        assert result2["repair_count"] == 2
        
        # Update state with repair_count = 2
        state["repair_count"] = 2
        
        # Third iteration: repair_count = 2 (should force approval)
        result3 = critic_node(state)
        assert result3["critic_verdict"] == "approved"
        assert result3["confidence_score"] == 0.3
        # repair_count should not be incremented further
        assert result3.get("repair_count", 2) == 2
        
        # Verify routing stops the loop
        route = route_after_critic({"repair_count": 2, "critic_verdict": "approved"})
        assert route == "memory_write"
    
    def test_repair_count_never_negative(self):
        """
        Edge case: Verify repair_count never becomes negative.
        """
        state: AgentState = {
            "repair_count": 0,
            "draft_response": "Valid response with $100 million.",
            "citations": [{"chunk_id": 1, "relevance_score": 0.9}],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Revenue was $100 million.",
                        "chunk_id": 1
                    }
                }
            ]
        }
        
        result = critic_node(state)
        
        # Should approve without incrementing
        assert result["critic_verdict"] == "approved"
        updated_repair_count = result.get("repair_count", 0)
        assert updated_repair_count >= 0, "repair_count must never be negative"
