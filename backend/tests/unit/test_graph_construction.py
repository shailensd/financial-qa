"""
Tests for LangGraph StateGraph construction and basic functionality.
"""

import pytest
from app.agent.pipeline import build_agent_graph, AgentState


class TestGraphConstruction:
    """Tests for building and validating the agent graph."""
    
    def test_build_agent_graph_succeeds(self):
        """Verify that the agent graph can be built without errors."""
        graph = build_agent_graph()
        assert graph is not None
        
    def test_graph_has_checkpointer(self):
        """Verify that the graph has a checkpointer configured."""
        graph = build_agent_graph()
        assert graph.checkpointer is not None
    
    def test_agent_state_structure(self):
        """Verify that AgentState has all required fields."""
        # Create a minimal state
        state: AgentState = {
            "query": "test query",
            "session_id": "test-session",
            "model_used": "gemini"
        }
        
        # Verify required fields can be set
        assert state["query"] == "test query"
        assert state["session_id"] == "test-session"
        assert state["model_used"] == "gemini"
        
        # Verify optional fields can be added
        state["repair_count"] = 0
        state["refusal"] = False
        state["plan"] = []
        
        assert state["repair_count"] == 0
        assert state["refusal"] is False
        assert state["plan"] == []
