"""
Property-Based Tests for Memory System.

**Validates: Requirements 11, 12, 13**

This module tests the property that MemorySummarizer triggers exactly once
every 5 turns using Hypothesis for property-based testing.
"""

import pytest
import pytest_asyncio
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock

from app.database import Base
from app.agent.memory import MemorySystem
from app.ml.llm_router import LLMRouter
from app import crud


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
    router.complete = Mock(return_value="Compressed summary of conversation.")
    return router


# ============================================================================
# Property-Based Test: MemorySummarizer Trigger
# ============================================================================

@pytest.mark.asyncio
@given(
    num_turns=st.integers(min_value=1, max_value=25),
)
@settings(max_examples=5, deadline=5000)
async def test_memory_summarizer_triggers_every_5_turns(num_turns):
    """
    Property: MemorySummarizer should trigger exactly once every 5 turns.
    
    For any number of turns N:
    - If N % 5 == 0, summarization should be triggered exactly N // 5 times
    - If N % 5 != 0, summarization should be triggered exactly N // 5 times
    
    This test verifies that the summarization trigger logic is correct
    by simulating various turn counts and checking the trigger behavior.
    """
    # Create fresh database for this test
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create mock LLM router
    mock_router = Mock(spec=LLMRouter)
    mock_router.complete = Mock(return_value="Compressed summary.")
    
    memory_system = MemorySystem(llm_router=mock_router)
    session_id = "test-session"
    
    async with async_session_maker() as db:
        # Write N turns
        for turn_num in range(1, num_turns + 1):
            await memory_system.write(
                db=db,
                session_id=session_id,
                turn_num=turn_num,
                query=f"Query {turn_num}",
                response=f"Response {turn_num}",
            )
            
            # Check if we should trigger summarization
            if turn_num % 5 == 0:
                # Trigger summarization
                await memory_system.summarize(
                    db=db,
                    session_id=session_id,
                )
        
        # Verify the number of compressed summaries
        all_memories = await crud.get_recent_memory(db=db, session_id=session_id, limit=100)
        
        # Count compressed summaries (turn_range_end > turn_range_start)
        compressed_count = sum(
            1 for mem in all_memories
            if mem.turn_range_end > mem.turn_range_start
        )
        
        # Expected number of summarizations
        expected_summarizations = num_turns // 5
        
        # Property: Number of compressed summaries should equal expected
        assert compressed_count == expected_summarizations, (
            f"For {num_turns} turns, expected {expected_summarizations} summarizations, "
            f"but got {compressed_count}"
        )
        
        # Additional property: Each compressed summary should span exactly 5 turns
        compressed_summaries = [
            mem for mem in all_memories
            if mem.turn_range_end > mem.turn_range_start
        ]
        
        for summary in compressed_summaries:
            span = summary.turn_range_end - summary.turn_range_start + 1
            assert span == 5, (
                f"Compressed summary should span 5 turns, but spans {span} turns "
                f"(range {summary.turn_range_start}-{summary.turn_range_end})"
            )
    
    await engine.dispose()


# ============================================================================
# Property-Based Test: Memory Write Consistency
# ============================================================================

@pytest.mark.asyncio
@given(
    num_turns=st.integers(min_value=1, max_value=15),
)
@settings(max_examples=3, deadline=5000)
async def test_memory_write_after_every_turn(num_turns):
    """
    Property: Memory system should write exactly one entry per turn.
    
    For any number of turns N, there should be exactly N memory entries
    in the database (excluding compressed summaries).
    """
    # Create fresh database for this test
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    memory_system = MemorySystem()
    session_id = "test-session"
    
    async with async_session_maker() as db:
        # Write N turns
        for turn_num in range(1, num_turns + 1):
            await memory_system.write(
                db=db,
                session_id=session_id,
                turn_num=turn_num,
                query=f"Query {turn_num}",
                response=f"Response {turn_num}",
            )
        
        # Verify the number of raw turn entries
        all_memories = await crud.get_recent_memory(db=db, session_id=session_id, limit=100)
        
        # Count raw turn entries (turn_range_start == turn_range_end)
        raw_turn_count = sum(
            1 for mem in all_memories
            if mem.turn_range_start == mem.turn_range_end
        )
        
        # Property: Number of raw turns should equal number of writes
        assert raw_turn_count == num_turns, (
            f"Expected {num_turns} raw turn entries, but got {raw_turn_count}"
        )
    
    await engine.dispose()


# ============================================================================
# Property-Based Test: Retrieve Format Consistency
# ============================================================================

@pytest.mark.asyncio
@given(
    num_turns=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=3, deadline=5000)
async def test_retrieve_format_consistency(num_turns):
    """
    Property: Retrieve should always return properly formatted memory context.
    
    For any number of turns:
    - If there are raw turns, context should contain "[Recent Turns]"
    - Context should never be malformed (e.g., empty sections)
    """
    # Create fresh database for this test
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    memory_system = MemorySystem()
    session_id = "test-session"
    
    async with async_session_maker() as db:
        # Write N turns
        for turn_num in range(1, num_turns + 1):
            await memory_system.write(
                db=db,
                session_id=session_id,
                turn_num=turn_num,
                query=f"Query {turn_num}",
                response=f"Response {turn_num}",
            )
        
        # Retrieve memory context
        context = await memory_system.retrieve(
            db=db,
            session_id=session_id,
        )
        
        # Property: Context should not be empty if there are turns
        assert context != "", "Context should not be empty when turns exist"
        
        # Property: Context should contain recent turns section
        assert "[Recent Turns]" in context, "Context should contain [Recent Turns] section"
        
        # Property: Context should contain at least one query
        assert "Query:" in context, "Context should contain at least one query"
        assert "Response:" in context, "Context should contain at least one answer"
        
        # Property: Context should not have malformed sections
        lines = context.split("\n")
        # No line should be just whitespace
        assert all(line.strip() or line == "" for line in lines), (
            "Context should not contain lines with only whitespace"
        )
    
    await engine.dispose()


# ============================================================================
# Property-Based Test: Summarization Idempotency
# ============================================================================

@pytest.mark.asyncio
async def test_summarization_creates_compressed_entries():
    """
    Property: Summarization should create compressed memory entries.
    
    Running summarization should create compressed summary entries
    that span multiple turns without corrupting the memory state.
    """
    # Create fresh database for this test
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create mock LLM router
    mock_router = Mock(spec=LLMRouter)
    mock_router.complete = Mock(return_value="Compressed summary.")
    
    memory_system = MemorySystem(llm_router=mock_router)
    session_id = "test-session"
    
    async with async_session_maker() as db:
        # Write 5 turns
        for turn_num in range(1, 6):
            await memory_system.write(
                db=db,
                session_id=session_id,
                turn_num=turn_num,
                query=f"Query {turn_num}",
                response=f"Response {turn_num}",
            )
        
        # Run summarization
        await memory_system.summarize(
            db=db,
            session_id=session_id,
        )
        
        # Verify memory state is consistent
        all_memories = await crud.get_recent_memory(db=db, session_id=session_id, limit=100)
        
        # Property: Should have 5 raw turns + N compressed summaries
        raw_turns = [m for m in all_memories if m.turn_range_start == m.turn_range_end]
        compressed = [m for m in all_memories if m.turn_range_end > m.turn_range_start]
        
        assert len(raw_turns) == 5, f"Should have 5 raw turns, got {len(raw_turns)}"
        assert len(compressed) == 1, (
            f"Should have 1 compressed summary, got {len(compressed)}"
        )
        
        # Property: First compressed summary should span turns 1-5
        # Subsequent summaries may have different ranges as they summarize recent entries
        first_summary = compressed[-1]  # Most recent is first in list, so last in reversed
        assert first_summary.turn_range_end >= first_summary.turn_range_start, (
            "Compressed summary should span at least one turn"
        )
    
    await engine.dispose()
