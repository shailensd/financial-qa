# LangGraph StateGraph Implementation

## Overview

This document describes the implementation of the LangGraph StateGraph for the Planner-Executor-Critic agent pipeline with repair loop functionality.

## Implementation Summary

### 1. AgentState TypedDict

Defined a comprehensive `AgentState` TypedDict with all fields from the design document:

```python
class AgentState(TypedDict, total=False):
    # Input fields
    query: str
    session_id: str
    model_used: str
    company: Optional[str]
    
    # Configuration fields
    ollama_base_url: str
    gemini_api_key: str
    
    # Planner fields
    plan: List[Dict[str, Any]]
    
    # Executor fields
    tool_results: List[Dict[str, Any]]
    draft_response: str
    citations: List[Dict[str, Any]]
    
    # Critic fields
    critic_verdict: str
    critic_feedback: Optional[str]
    confidence_score: float
    
    # Repair loop fields
    repair_count: int
    
    # RefusalGuard fields
    refusal: bool
    refusal_reason: Optional[str]
    
    # Memory fields
    memory_context: str
    turn_count: int
    
    # Performance tracking
    latency_ms: int
```

### 2. Graph Nodes

Implemented all required nodes:

- **refusal_guard_node**: Checks queries against prohibited keywords
- **memory_retrieve_node**: Fetches session context (placeholder for now)
- **planner_node**: Decomposes queries into tool calls
- **executor_node**: Executes tools and generates draft response
- **critic_node**: Validates numerical accuracy and citation completeness
- **memory_write_node**: Persists turn to memory (placeholder for now)
- **memory_summarizer_node**: Compresses session history (placeholder for now)

### 3. Graph Structure

```
START → refusal_guard → (memory_retrieve | END)
                              ↓
                         planner
                              ↓
                         executor
                              ↓
                          critic → (planner [repair] | memory_write)
                                                            ↓
                                              (memory_summarizer | END)
                                                            ↓
                                                          END
```

### 4. Conditional Routing

Implemented three routing functions:

1. **route_after_refusal**: Routes to END if refused, memory_retrieve if allowed
2. **route_after_critic**: Routes to planner for repair (if repair_count < 2), otherwise to memory_write
3. **route_after_memory_write**: Routes to memory_summarizer every 5 turns, otherwise to END

### 5. Repair Loop Logic

The repair loop is bounded by `max_repair_iterations = 2`:

- When critic detects validation failures (numerical mismatch or missing citations), it increments `repair_count` and returns a repair verdict
- The routing function checks if `repair_count < 2` before allowing another repair iteration
- After 2 repair attempts, the critic forces approval with low confidence (0.3)

### 6. Checkpointing

Configured `MemorySaver` checkpointer for session continuity:

```python
checkpointer = MemorySaver()
compiled_graph = graph.compile(checkpointer=checkpointer)
```

Note: For production deployment, consider using a persistent checkpointer (e.g., PostgresSaver when available).

### 7. Property-Based Testing

Implemented comprehensive property-based tests using Hypothesis to verify:

1. **repair_count never exceeds 2**: The critic never increments repair_count beyond the maximum
2. **Forced approval at max iterations**: When repair_count >= 2, critic always approves regardless of validation failures
3. **Routing respects max iterations**: The routing function never routes back to planner when repair_count >= 2
4. **Repair loop terminates**: Integration test verifying the loop terminates after exactly 2 iterations

## Test Results

All tests pass successfully:

- ✅ 4/4 property-based tests for repair loop bounds
- ✅ 3/3 graph construction tests
- ✅ 67/67 existing pipeline node tests (planner, executor, critic, refusal_guard)

## Usage

To build and use the agent graph:

```python
from app.agent.pipeline import build_agent_graph, AgentState

# Build the graph
graph = build_agent_graph()

# Create initial state
initial_state: AgentState = {
    "query": "What was Apple's revenue in FY2023?",
    "session_id": "test-session-123",
    "model_used": "gemini",
    "ollama_base_url": "http://localhost:11434",
    "gemini_api_key": "your-api-key"
}

# Run the graph
config = {"configurable": {"thread_id": "test-session-123"}}
result = graph.invoke(initial_state, config)
```

## Next Steps

The following components have placeholder implementations and need to be completed:

1. **Memory System**: Implement actual database operations in memory_retrieve_node, memory_write_node, and memory_summarizer_node
2. **Structured Logging**: Integrate structured logging throughout the pipeline
3. **API Integration**: Wire the graph into FastAPI endpoints
4. **End-to-End Testing**: Test the complete graph execution with real LLM calls

## Files Modified/Created

- `backend/app/agent/pipeline.py`: Added AgentState, graph construction, routing functions, and memory node placeholders
- `backend/tests/unit/test_repair_loop.py`: Property-based tests for repair loop bounds
- `backend/tests/unit/test_graph_construction.py`: Tests for graph construction and structure
- `backend/LANGGRAPH_IMPLEMENTATION.md`: This documentation file
