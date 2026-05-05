"""
Unit tests for CRUD operations.

Tests verify each CRUD function against a test database, ensuring proper
creation, retrieval, and relationship loading with joinedload.
"""

import pytest
import pytest_asyncio
from datetime import datetime, date
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import crud
from app.models import Document, Chunk, Query, Response, Citation, MemorySummary, Log


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


# ============================================================================
# Document CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_document(test_db):
    """Test creating a document record."""
    document = await crud.create_document(
        db=test_db,
        company="Apple Inc.",
        filing_type="10-K",
        fiscal_year=2023,
        filing_date=date(2023, 11, 3),
        source_url="https://sec.gov/example",
        metadata_json={"pages": 120},
    )
    
    assert document.id is not None
    assert document.company == "Apple Inc."
    assert document.filing_type == "10-K"
    assert document.fiscal_year == 2023
    assert document.metadata_json == {"pages": 120}
    assert document.created_at is not None


# ============================================================================
# Chunk CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_chunk(test_db):
    """Test creating a chunk record with document relationship."""
    # Create parent document first
    document = await crud.create_document(
        db=test_db,
        company="Apple Inc.",
        filing_type="10-K",
        fiscal_year=2023,
        filing_date=date(2023, 11, 3),
        source_url="https://sec.gov/example",
    )
    
    # Create chunk
    chunk = await crud.create_chunk(
        db=test_db,
        document_id=document.id,
        chunk_text="Apple's revenue for FY2023 was $383.3 billion.",
        chunk_index=0,
        section_label="Item 7. MD&A",
        page_number=42,
    )
    
    assert chunk.id is not None
    assert chunk.document_id == document.id
    assert chunk.chunk_text == "Apple's revenue for FY2023 was $383.3 billion."
    assert chunk.section_label == "Item 7. MD&A"
    assert chunk.page_number == 42
    assert chunk.document is not None  # Verify relationship loaded
    assert chunk.document.company == "Apple Inc."


# ============================================================================
# Query CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_query(test_db):
    """Test creating a query record."""
    query = await crud.create_query(
        db=test_db,
        session_id="session-123",
        query_text="What was Apple's revenue in FY2023?",
        model_used="gemini",
    )
    
    assert query.id is not None
    assert query.session_id == "session-123"
    assert query.query_text == "What was Apple's revenue in FY2023?"
    assert query.model_used == "gemini"
    assert query.timestamp is not None


# ============================================================================
# Response CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_response(test_db):
    """Test creating a response record with query relationship."""
    # Create parent query first
    query = await crud.create_query(
        db=test_db,
        session_id="session-123",
        query_text="What was Apple's revenue in FY2023?",
        model_used="gemini",
    )
    
    # Create response
    response = await crud.create_response(
        db=test_db,
        query_id=query.id,
        response_text="Apple's revenue in FY2023 was $383.3 billion.",
        model_used="gemini",
        confidence_score=0.95,
        latency_ms=1500,
        refusal_flag=False,
        repair_count=0,
    )
    
    assert response.id is not None
    assert response.query_id == query.id
    assert response.confidence_score == 0.95
    assert response.latency_ms == 1500
    assert response.refusal_flag is False
    assert response.repair_count == 0
    assert response.query is not None  # Verify relationship loaded
    assert response.query.query_text == "What was Apple's revenue in FY2023?"


@pytest.mark.asyncio
async def test_create_response_with_refusal(test_db):
    """Test creating a response with refusal flag."""
    query = await crud.create_query(
        db=test_db,
        session_id="session-123",
        query_text="Should I buy Apple stock?",
        model_used="gemini",
    )
    
    response = await crud.create_response(
        db=test_db,
        query_id=query.id,
        response_text="I cannot provide investment advice.",
        model_used="gemini",
        confidence_score=1.0,
        latency_ms=500,
        refusal_flag=True,
        refusal_reason="investment_advice_prohibited",
    )
    
    assert response.refusal_flag is True
    assert response.refusal_reason == "investment_advice_prohibited"


# ============================================================================
# Citation CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_citation(test_db):
    """Test creating a citation with response and chunk relationships."""
    # Create document
    document = await crud.create_document(
        db=test_db,
        company="Apple Inc.",
        filing_type="10-K",
        fiscal_year=2023,
        filing_date=date(2023, 11, 3),
        source_url="https://sec.gov/example",
    )
    
    # Create chunk
    chunk = await crud.create_chunk(
        db=test_db,
        document_id=document.id,
        chunk_text="Revenue: $383.3 billion",
        chunk_index=0,
    )
    
    # Create query and response
    query = await crud.create_query(
        db=test_db,
        session_id="session-123",
        query_text="What was Apple's revenue?",
        model_used="gemini",
    )
    
    response = await crud.create_response(
        db=test_db,
        query_id=query.id,
        response_text="Apple's revenue was $383.3 billion.",
        model_used="gemini",
        confidence_score=0.95,
        latency_ms=1500,
    )
    
    # Create citation
    citation = await crud.create_citation(
        db=test_db,
        response_id=response.id,
        chunk_id=chunk.id,
        relevance_score=0.98,
    )
    
    assert citation.id is not None
    assert citation.response_id == response.id
    assert citation.chunk_id == chunk.id
    assert citation.relevance_score == 0.98
    assert citation.response is not None  # Verify relationship loaded
    assert citation.chunk is not None  # Verify relationship loaded
    assert citation.chunk.chunk_text == "Revenue: $383.3 billion"


# ============================================================================
# Memory CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_write_memory(test_db):
    """Test writing a memory summary."""
    memory = await crud.write_memory(
        db=test_db,
        session_id="session-123",
        turn_range_start=1,
        turn_range_end=1,
        summary_text="User asked about Apple's revenue.",
    )
    
    assert memory.id is not None
    assert memory.session_id == "session-123"
    assert memory.turn_range_start == 1
    assert memory.turn_range_end == 1
    assert memory.summary_text == "User asked about Apple's revenue."


@pytest.mark.asyncio
async def test_get_recent_memory(test_db):
    """Test retrieving recent memory summaries."""
    # Create multiple memory entries
    await crud.write_memory(
        db=test_db,
        session_id="session-123",
        turn_range_start=1,
        turn_range_end=1,
        summary_text="Turn 1 summary",
    )
    
    await crud.write_memory(
        db=test_db,
        session_id="session-123",
        turn_range_start=2,
        turn_range_end=2,
        summary_text="Turn 2 summary",
    )
    
    await crud.write_memory(
        db=test_db,
        session_id="session-123",
        turn_range_start=3,
        turn_range_end=3,
        summary_text="Turn 3 summary",
    )
    
    # Get most recent memory
    recent = await crud.get_recent_memory(db=test_db, session_id="session-123", limit=1)
    
    assert len(recent) == 1
    assert recent[0].summary_text == "Turn 3 summary"


@pytest.mark.asyncio
async def test_get_raw_turns(test_db):
    """Test retrieving raw query-response turns."""
    # Create multiple turns
    for i in range(3):
        query = await crud.create_query(
            db=test_db,
            session_id="session-123",
            query_text=f"Query {i+1}",
            model_used="gemini",
        )
        
        await crud.create_response(
            db=test_db,
            query_id=query.id,
            response_text=f"Response {i+1}",
            model_used="gemini",
            confidence_score=0.9,
            latency_ms=1000,
        )
    
    # Get last 2 turns
    turns = await crud.get_raw_turns(db=test_db, session_id="session-123", limit=2)
    
    assert len(turns) == 2
    # Most recent first
    assert turns[0][0].query_text == "Query 3"
    assert turns[0][1].response_text == "Response 3"
    assert turns[1][0].query_text == "Query 2"


@pytest.mark.asyncio
async def test_get_session_history(test_db):
    """Test retrieving complete session history."""
    # Create multiple turns
    for i in range(3):
        query = await crud.create_query(
            db=test_db,
            session_id="session-123",
            query_text=f"Query {i+1}",
            model_used="gemini",
        )
        
        await crud.create_response(
            db=test_db,
            query_id=query.id,
            response_text=f"Response {i+1}",
            model_used="gemini",
            confidence_score=0.9,
            latency_ms=1000,
        )
    
    # Get full history
    history = await crud.get_session_history(db=test_db, session_id="session-123")
    
    assert len(history) == 3
    # Oldest first
    assert history[0][0].query_text == "Query 1"
    assert history[1][0].query_text == "Query 2"
    assert history[2][0].query_text == "Query 3"


# ============================================================================
# Log CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_log(test_db):
    """Test creating a structured log entry."""
    # Create query first
    query = await crud.create_query(
        db=test_db,
        session_id="session-123",
        query_text="Test query",
        model_used="gemini",
    )
    
    # Create log
    log = await crud.create_log(
        db=test_db,
        session_id="session-123",
        query_id=query.id,
        log_json={
            "plan": [{"tool": "LOOKUP", "inputs": {"entity": "Apple"}}],
            "tool_results": [{"output": "Revenue data"}],
            "critic_verdict": "approved",
        },
    )
    
    assert log.id is not None
    assert log.session_id == "session-123"
    assert log.query_id == query.id
    assert log.log_json["critic_verdict"] == "approved"
    assert log.query is not None  # Verify relationship loaded


@pytest.mark.asyncio
async def test_get_logs_by_session(test_db):
    """Test retrieving logs filtered by session."""
    # Create queries and logs for two sessions
    for session_num in [1, 2]:
        for i in range(2):
            query = await crud.create_query(
                db=test_db,
                session_id=f"session-{session_num}",
                query_text=f"Query {i}",
                model_used="gemini",
            )
            
            await crud.create_log(
                db=test_db,
                session_id=f"session-{session_num}",
                query_id=query.id,
                log_json={"data": f"log-{session_num}-{i}"},
            )
    
    # Get logs for session-1 only
    logs = await crud.get_logs(db=test_db, session_id="session-1")
    
    assert len(logs) == 2
    assert all(log.session_id == "session-1" for log in logs)


@pytest.mark.asyncio
async def test_get_logs_by_query(test_db):
    """Test retrieving logs filtered by query ID."""
    # Create query
    query = await crud.create_query(
        db=test_db,
        session_id="session-123",
        query_text="Test query",
        model_used="gemini",
    )
    
    # Create log
    await crud.create_log(
        db=test_db,
        session_id="session-123",
        query_id=query.id,
        log_json={"data": "test"},
    )
    
    # Get logs for this query
    logs = await crud.get_logs(db=test_db, query_id=query.id)
    
    assert len(logs) == 1
    assert logs[0].query_id == query.id
    assert logs[0].log_json["data"] == "test"
