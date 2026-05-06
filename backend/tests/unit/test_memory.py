"""
Unit tests for Memory System.

Tests verify write-after-every-turn, summarize-every-5-turns trigger,
and retrieve format functionality.
"""

import pytest
import pytest_asyncio
from datetime import datetime, date
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, AsyncMock, patch

from app.database import Base
from app import crud
from app.agent.memory import MemorySystem
from app.ml.llm_router import LLMRouter


# ============================================================================
# Test Database Setup
# ============================================================================

@pytest_asyncio.fixture
async def test_db():
    """
    Create an in-memory SQLite database for testing.
    
    Yields an async session for each test, then tears down the database.
    """
    # Create in-memory async SQLite engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Yield session for test
    async with async_session_maker() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router for testing."""
    router = Mock(spec=LLMRouter)
    router.complete = Mock(return_value="Compressed summary of the conversation covering Apple revenue and financial metrics.")
    return router


# ============================================================================
# Memory Write Tests
# ============================================================================

@pytest.mark.asyncio
async def test_write_memory_basic(test_db):
    """Test writing a basic memory entry."""
    memory_system = MemorySystem()
    
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=1,
        query="What was Apple's revenue in FY2023?",
        response="Apple's revenue in FY2023 was $383.3 billion.",
    )
    
    # Verify memory was written
    memories = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=1)
    assert len(memories) == 1
    assert memories[0].session_id == "session-123"
    assert memories[0].turn_range_start == 1
    assert memories[0].turn_range_end == 1
    assert "Apple" in memories[0].summary_text
    assert "revenue" in memories[0].summary_text


@pytest.mark.asyncio
async def test_write_memory_extracts_entities(test_db):
    """Test that write extracts key entities from query and response."""
    memory_system = MemorySystem()
    
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=1,
        query="Compare Microsoft and Amazon revenue growth",
        response="Microsoft had 12% growth while Amazon had 9% growth in Q3.",
    )
    
    # Verify entities were extracted
    memories = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=1)
    summary_text = memories[0].summary_text
    
    # Should contain entities section
    assert "[Entities:" in summary_text
    # Should extract company names
    assert "Microsoft" in summary_text or "Amazon" in summary_text
    # Should extract financial terms
    assert "revenue" in summary_text or "growth" in summary_text


@pytest.mark.asyncio
async def test_write_memory_multiple_turns(test_db):
    """Test writing multiple turns in sequence."""
    memory_system = MemorySystem()
    
    # Write 3 turns
    for i in range(1, 4):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=f"Query {i}",
            response=f"Response {i}",
        )
    
    # Verify all turns were written
    memories = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=10)
    assert len(memories) == 3
    
    # Verify turn numbers are correct (most recent first)
    assert memories[0].turn_range_start == 3
    assert memories[1].turn_range_start == 2
    assert memories[2].turn_range_start == 1


# ============================================================================
# Memory Retrieve Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retrieve_empty_session(test_db):
    """Test retrieving memory from an empty session."""
    memory_system = MemorySystem()
    
    context = await memory_system.retrieve(
        db=test_db,
        session_id="session-empty",
    )
    
    assert context == ""


@pytest.mark.asyncio
async def test_retrieve_recent_turns_only(test_db):
    """Test retrieving memory with only raw turns (no compressed summary)."""
    memory_system = MemorySystem()
    
    # Write 2 turns
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=1,
        query="What is Apple's revenue?",
        response="Apple's revenue is $383.3 billion.",
    )
    
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=2,
        query="What about Microsoft?",
        response="Microsoft's revenue is $211.9 billion.",
    )
    
    # Retrieve memory context
    context = await memory_system.retrieve(
        db=test_db,
        session_id="session-123",
    )
    
    # Should contain recent turns section
    assert "[Recent Turns]" in context
    assert "Apple" in context
    assert "Microsoft" in context
    # Should be in chronological order
    assert context.index("Apple") < context.index("Microsoft")


@pytest.mark.asyncio
async def test_retrieve_with_compressed_summary(test_db):
    """Test retrieving memory with a compressed summary."""
    memory_system = MemorySystem()
    
    # Write a compressed summary (turn_range_start < turn_range_end)
    await crud.write_memory(
        db=test_db,
        session_id="session-123",
        turn_range_start=1,
        turn_range_end=5,
        summary_text="User asked about Apple, Microsoft, and Amazon revenue. Discussed growth rates and profitability.",
    )
    
    # Write 2 recent raw turns
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=6,
        query="What about Tesla?",
        response="Tesla's revenue is $96.8 billion.",
    )
    
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=7,
        query="Compare to Google",
        response="Google's revenue is $307.4 billion.",
    )
    
    # Retrieve memory context
    context = await memory_system.retrieve(
        db=test_db,
        session_id="session-123",
    )
    
    # Should contain both sections
    assert "[Session Summary]" in context
    assert "[Recent Turns]" in context
    
    # Should contain compressed summary
    assert "Apple, Microsoft, and Amazon" in context
    
    # Should contain recent turns
    assert "Tesla" in context
    assert "Google" in context


@pytest.mark.asyncio
async def test_retrieve_limits_to_last_2_turns(test_db):
    """Test that retrieve only fetches the last 2 raw turns."""
    memory_system = MemorySystem()
    
    # Write 5 turns
    for i in range(1, 6):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=f"Query {i}",
            response=f"Response {i}",
        )
    
    # Retrieve memory context
    context = await memory_system.retrieve(
        db=test_db,
        session_id="session-123",
    )
    
    # Should only contain last 2 turns
    assert "Query 4" in context
    assert "Query 5" in context
    assert "Query 1" not in context
    assert "Query 2" not in context
    assert "Query 3" not in context


# ============================================================================
# Memory Summarize Tests
# ============================================================================

@pytest.mark.asyncio
async def test_summarize_basic(test_db, mock_llm_router):
    """Test basic summarization of 5 turns."""
    memory_system = MemorySystem(llm_router=mock_llm_router)
    
    # Write 5 turns
    for i in range(1, 6):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=f"Query {i} about Apple revenue",
            response=f"Response {i} with financial data",
        )
    
    # Summarize
    await memory_system.summarize(
        db=test_db,
        session_id="session-123",
    )
    
    # Verify LLM was called
    assert mock_llm_router.complete.called
    call_args = mock_llm_router.complete.call_args
    # Check keyword arguments
    assert call_args.kwargs["model"] == "gemini"  # Model name
    messages = call_args.kwargs["messages"]
    assert len(messages) == 2
    assert "summarization assistant" in messages[0]["content"].lower()
    
    # Verify compressed summary was written
    memories = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=1)
    compressed = memories[0]
    
    # Should span turns 1-5
    assert compressed.turn_range_start == 1
    assert compressed.turn_range_end == 5
    
    # Should contain the LLM-generated summary
    assert "Compressed summary" in compressed.summary_text


@pytest.mark.asyncio
async def test_summarize_no_llm_router_raises_error(test_db):
    """Test that summarize raises error when no LLM router is available."""
    memory_system = MemorySystem()  # No router provided
    
    # Write some turns
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=1,
        query="Test query",
        response="Test response",
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="LLM router is required"):
        await memory_system.summarize(
            db=test_db,
            session_id="session-123",
        )


@pytest.mark.asyncio
async def test_summarize_with_provided_router(test_db, mock_llm_router):
    """Test that summarize can use a provided router instead of instance router."""
    memory_system = MemorySystem()  # No router in constructor
    
    # Write turns
    for i in range(1, 6):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=f"Query {i}",
            response=f"Response {i}",
        )
    
    # Summarize with provided router
    await memory_system.summarize(
        db=test_db,
        session_id="session-123",
        llm_router=mock_llm_router,
    )
    
    # Should work without error
    assert mock_llm_router.complete.called


@pytest.mark.asyncio
async def test_summarize_empty_session(test_db, mock_llm_router):
    """Test that summarize handles empty sessions gracefully."""
    memory_system = MemorySystem(llm_router=mock_llm_router)
    
    # Summarize empty session (should do nothing)
    await memory_system.summarize(
        db=test_db,
        session_id="session-empty",
    )
    
    # LLM should not be called
    assert not mock_llm_router.complete.called


@pytest.mark.asyncio
async def test_summarize_insufficient_turns(test_db, mock_llm_router):
    """Test that summarize does not trigger with fewer than 5 turns."""
    memory_system = MemorySystem(llm_router=mock_llm_router)
    
    # Write only 3 turns
    for i in range(1, 4):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=f"Query {i}",
            response=f"Response {i}",
        )
    
    # Attempt to summarize (should do nothing)
    await memory_system.summarize(
        db=test_db,
        session_id="session-123",
    )
    
    # LLM should not be called (not enough turns)
    assert not mock_llm_router.complete.called
    
    # Verify no compressed summary was created
    memories = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=10)
    compressed = [m for m in memories if m.turn_range_end > m.turn_range_start]
    assert len(compressed) == 0


@pytest.mark.asyncio
async def test_summarize_every_5_turns_trigger(test_db, mock_llm_router):
    """
    Test that summarization should be triggered every 5 turns.
    
    This test simulates the agent pipeline's trigger logic:
    - After turn 5: summarize (turn_count % 5 == 0)
    - After turn 10: summarize again (turn_count % 5 == 0)
    - After turn 7: do not summarize (turn_count % 5 != 0)
    """
    memory_system = MemorySystem(llm_router=mock_llm_router)
    
    # Write 10 turns and trigger summarization at turns 5 and 10
    for turn_num in range(1, 11):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=turn_num,
            query=f"Query {turn_num}",
            response=f"Response {turn_num}",
        )
        
        # Simulate the agent pipeline's trigger logic
        if turn_num % 5 == 0:
            await memory_system.summarize(
                db=test_db,
                session_id="session-123",
            )
    
    # Verify LLM was called exactly twice (at turns 5 and 10)
    assert mock_llm_router.complete.call_count == 2
    
    # Verify two compressed summaries were created
    memories = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=20)
    compressed = [m for m in memories if m.turn_range_end > m.turn_range_start]
    assert len(compressed) == 2
    
    # Verify the first summary spans turns 1-5
    # Note: memories are in descending order, so the oldest is last
    first_summary = compressed[-1]
    assert first_summary.turn_range_start == 1
    assert first_summary.turn_range_end == 5
    
    # Verify the second summary spans turns 6-10
    second_summary = compressed[0]
    assert second_summary.turn_range_start == 6
    assert second_summary.turn_range_end == 10


# ============================================================================
# Entity Extraction Tests
# ============================================================================

def test_extract_entities_companies():
    """Test extraction of company names."""
    memory_system = MemorySystem()
    
    entities = memory_system._extract_entities(
        query="Compare Apple and Microsoft",
        response="Apple has higher revenue than Microsoft"
    )
    
    assert "Apple" in entities
    assert "Microsoft" in entities


def test_extract_entities_financial_terms():
    """Test extraction of financial terms."""
    memory_system = MemorySystem()
    
    entities = memory_system._extract_entities(
        query="What is the revenue and profit margin?",
        response="Revenue is $100B with 25% margin"
    )
    
    assert "revenue" in entities
    assert "margin" in entities


def test_extract_entities_mixed():
    """Test extraction of both companies and financial terms."""
    memory_system = MemorySystem()
    
    entities = memory_system._extract_entities(
        query="What was Amazon's EBITDA in fiscal year 2023?",
        response="Amazon's EBITDA was $50B in FY 2023"
    )
    
    # Should extract company
    assert any("Amazon" in e or "AMZN" in e for e in entities)
    # Should extract financial terms
    assert "EBITDA" in entities
    # Should extract time period (FY 2023 or similar)
    assert any("FY" in e for e in entities)


def test_extract_entities_case_insensitive():
    """Test that entity extraction is case-insensitive."""
    memory_system = MemorySystem()
    
    entities = memory_system._extract_entities(
        query="what is APPLE's REVENUE?",
        response="apple's revenue is high"
    )
    
    # Should extract regardless of case
    assert any("apple" in e.lower() for e in entities)
    assert any("revenue" in e.lower() for e in entities)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_write_retrieve_integration(test_db):
    """Test write followed by retrieve in a realistic scenario."""
    memory_system = MemorySystem()
    
    # Simulate a conversation
    turns = [
        ("What was Apple's revenue in FY2023?", "Apple's revenue in FY2023 was $383.3 billion."),
        ("How does that compare to FY2022?", "In FY2022, Apple's revenue was $394.3 billion, so there was a decline."),
        ("What about profit margins?", "Apple's profit margin in FY2023 was 25.3%."),
    ]
    
    for i, (query, response) in enumerate(turns, start=1):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=query,
            response=response,
        )
    
    # Retrieve memory context
    context = await memory_system.retrieve(
        db=test_db,
        session_id="session-123",
    )
    
    # Should contain last 2 turns
    assert "FY2022" in context  # Turn 2
    assert "profit margin" in context  # Turn 3
    # Should not contain first turn
    assert "FY2023 was $383.3 billion" not in context


@pytest.mark.asyncio
async def test_full_memory_lifecycle(test_db, mock_llm_router):
    """Test complete memory lifecycle: write, summarize, retrieve."""
    memory_system = MemorySystem(llm_router=mock_llm_router)
    
    # Write 5 turns
    for i in range(1, 6):
        await memory_system.write(
            db=test_db,
            session_id="session-123",
            turn_num=i,
            query=f"Query {i} about financial metrics",
            response=f"Response {i} with data",
        )
    
    # Summarize after 5 turns
    await memory_system.summarize(
        db=test_db,
        session_id="session-123",
    )
    
    # Write 2 more turns
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=6,
        query="New query after summarization",
        response="New response",
    )
    
    await memory_system.write(
        db=test_db,
        session_id="session-123",
        turn_num=7,
        query="Another query",
        response="Another response",
    )
    
    # Retrieve memory context
    context = await memory_system.retrieve(
        db=test_db,
        session_id="session-123",
    )
    
    # Should have both summary and recent turns
    assert "[Session Summary]" in context
    assert "[Recent Turns]" in context
    
    # Summary should contain compressed content
    assert "Compressed summary" in context
    
    # Recent turns should contain turns 6 and 7
    assert "New query after summarization" in context
    assert "Another query" in context


# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, strategies as st, settings


@given(st.integers(min_value=1, max_value=100))
@settings(max_examples=50, deadline=None)
def test_memory_summarizer_triggers_exactly_once_every_5_turns(turn_count):
    """
    Property-based test: MemorySummarizer triggers exactly once every 5 turns.
    
    This test verifies the correctness property that the memory summarization
    logic (turn_count % 5 == 0) triggers at exactly the right intervals:
    - Triggers at turns: 5, 10, 15, 20, 25, ...
    - Does NOT trigger at turns: 1, 2, 3, 4, 6, 7, 8, 9, 11, ...
    
    The test simulates the agent pipeline's routing logic by checking the
    route_after_memory_write function's behavior for arbitrary turn counts.
    
    Property: For any turn_count N:
    - If N % 5 == 0: route_after_memory_write MUST return "memory_summarizer"
    - If N % 5 != 0: route_after_memory_write MUST return "end"
    """
    from app.agent.pipeline import route_after_memory_write
    
    # Create state with the given turn_count
    state = {"turn_count": turn_count}
    
    # Call the routing function
    route = route_after_memory_write(state)
    
    # Verify the property: triggers if and only if turn_count % 5 == 0
    if turn_count % 5 == 0:
        assert route == "memory_summarizer", (
            f"MemorySummarizer MUST trigger at turn {turn_count} "
            f"(turn_count % 5 == 0), but route was '{route}'"
        )
    else:
        assert route == "end", (
            f"MemorySummarizer MUST NOT trigger at turn {turn_count} "
            f"(turn_count % 5 == {turn_count % 5}), but route was '{route}'"
        )


@pytest.mark.asyncio
async def test_memory_summarizer_trigger_sequence(test_db, mock_llm_router):
    """
    Integration test: Verify MemorySummarizer triggers at correct intervals in a sequence.
    
    This test simulates a realistic conversation flow and verifies that
    summarization happens at exactly turns 5, 10, 15, etc.
    """
    from app.agent.pipeline import route_after_memory_write
    
    memory_system = MemorySystem(llm_router=mock_llm_router)
    
    # Track when summarization should trigger
    expected_trigger_turns = {5, 10, 15, 20}
    actual_trigger_turns = set()
    
    # Simulate 20 turns
    for turn_num in range(1, 21):
        # Write memory for this turn
        await memory_system.write(
            db=test_db,
            session_id="session-prop-test",
            turn_num=turn_num,
            query=f"Query {turn_num}",
            response=f"Response {turn_num}",
        )
        
        # Check routing decision
        state = {"turn_count": turn_num}
        route = route_after_memory_write(state)
        
        # If route says to summarize, do it and track the turn
        if route == "memory_summarizer":
            actual_trigger_turns.add(turn_num)
            await memory_system.summarize(
                db=test_db,
                session_id="session-prop-test",
            )
    
    # Verify triggers happened at exactly the expected turns
    assert actual_trigger_turns == expected_trigger_turns, (
        f"MemorySummarizer triggered at turns {actual_trigger_turns}, "
        f"but should have triggered at {expected_trigger_turns}"
    )
    
    # Verify LLM was called exactly 4 times (once per trigger)
    assert mock_llm_router.complete.call_count == 4, (
        f"LLM should be called 4 times (turns 5, 10, 15, 20), "
        f"but was called {mock_llm_router.complete.call_count} times"
    )
    
    # Verify compressed summaries were created at the right intervals
    memories = await crud.get_recent_memory(db=test_db, session_id="session-prop-test", limit=50)
    compressed = [m for m in memories if m.turn_range_end > m.turn_range_start]
    
    # Should have 4 compressed summaries
    assert len(compressed) == 4, (
        f"Should have 4 compressed summaries, but found {len(compressed)}"
    )
    
    # Verify the turn ranges of compressed summaries
    # Note: memories are in descending order (most recent first)
    expected_ranges = [(16, 20), (11, 15), (6, 10), (1, 5)]
    actual_ranges = [(m.turn_range_start, m.turn_range_end) for m in compressed]
    
    assert actual_ranges == expected_ranges, (
        f"Compressed summary ranges {actual_ranges} do not match expected {expected_ranges}"
    )
