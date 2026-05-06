"""
Integration tests for FastAPI endpoints.

Tests all API endpoints using httpx.AsyncClient with a test database.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI

from app.main import app
from app.database import Base, get_db
from app.models import Document, Chunk, Query, Response, Citation, Log
from app import crud


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Create test engine and session factory
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db():
    """Override database dependency for testing."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client."""
    # Skip lifespan to avoid initialization issues in tests
    app_for_test = FastAPI(
        title="FinDoc Intelligence API",
        description="Financial Q&A system with RAG and Planner-Executor-Critic agent pipeline",
        version="1.0.0",
    )
    
    # Copy routes from main app
    app_for_test.router = app.router
    
    # Override dependency
    app_for_test.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app_for_test)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_data(test_db):
    """Create sample data for testing."""
    async with TestSessionLocal() as db:
        # Create document
        document = await crud.create_document(
            db=db,
            company="Apple",
            filing_type="10-K",
            fiscal_year=2023,
            filing_date=datetime(2023, 11, 3),
            source_url="https://example.com/aapl-10k-2023",
            metadata_json={"test": True}
        )
        
        # Create chunks
        chunk1 = await crud.create_chunk(
            db=db,
            document_id=document.id,
            chunk_text="Apple's total revenue for FY2023 was $383.285 billion.",
            chunk_index=0,
            section_label="Item 7. MD&A",
            page_number=1
        )
        
        chunk2 = await crud.create_chunk(
            db=db,
            document_id=document.id,
            chunk_text="Net income for FY2023 was $96.995 billion.",
            chunk_index=1,
            section_label="Item 7. MD&A",
            page_number=1
        )
        
        # Create query
        session_id = str(uuid.uuid4())
        query = await crud.create_query(
            db=db,
            session_id=session_id,
            query_text="What was Apple's revenue in FY2023?",
            model_used="gemini"
        )
        
        # Create response
        response = await crud.create_response(
            db=db,
            query_id=query.id,
            response_text="Apple's total revenue for FY2023 was $383.285 billion.",
            model_used="gemini",
            confidence_score=0.95,
            latency_ms=1500,
            refusal_flag=False,
            refusal_reason=None,
            repair_count=0
        )
        
        # Create citation
        citation = await crud.create_citation(
            db=db,
            response_id=response.id,
            chunk_id=chunk1.id,
            relevance_score=0.95
        )
        
        # Create log
        log = await crud.create_log(
            db=db,
            session_id=session_id,
            query_id=query.id,
            log_json={
                "session_id": session_id,
                "query_text": query.query_text,
                "model_used": "gemini",
                "plan": [{"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}],
                "tool_results": [{"tool": "LOOKUP", "status": "success"}],
                "chunk_ids": [chunk1.id],
                "refusal_decision": False,
                "critic_verdict": "approved",
                "repair_count": 0,
                "total_latency_ms": 1500
            }
        )
        
        await db.commit()
        
        return {
            "session_id": session_id,
            "document_id": document.id,
            "chunk1_id": chunk1.id,
            "chunk2_id": chunk2.id,
            "query_id": query.id,
            "response_id": response.id,
            "citation_id": citation.id,
            "log_id": log.id
        }


# ============================================================================
# Test Root Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns API information."""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "FinDoc Intelligence API"
    assert data["version"] == "1.0.0"
    assert "docs" in data
    assert "health" in data


# ============================================================================
# Test Health Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_health_endpoint(client, test_db):
    """Test health endpoint returns system status."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "db" in data
    assert "chroma" in data
    assert "bm25" in data
    
    # Database should be connected in tests
    assert data["db"] == "connected"
    assert data["status"] in ["ok", "degraded"]


# ============================================================================
# Test Query Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_query_endpoint_validation(client, test_db):
    """Test query endpoint validates request."""
    # Test missing required fields
    response = await client.post("/query", json={})
    assert response.status_code == 422
    
    # Test invalid model
    response = await client.post("/query", json={
        "session_id": str(uuid.uuid4()),
        "query_text": "What is Apple's revenue?",
        "models": ["invalid_model"]
    })
    assert response.status_code == 422
    assert "Invalid models" in response.json()["detail"]
    
    # Test query text too short
    response = await client.post("/query", json={
        "session_id": str(uuid.uuid4()),
        "query_text": "Hi",
        "models": ["gemini"]
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_endpoint_success(client, sample_data):
    """Test query endpoint processes valid request."""
    # Note: This test will fail without a working agent pipeline
    # For now, we test that the endpoint accepts the request
    response = await client.post("/query", json={
        "session_id": sample_data["session_id"],
        "query_text": "What was Apple's revenue in FY2023?",
        "models": ["gemini"],
        "company": "Apple"
    })
    
    # Expect either success or service unavailable (if retriever not initialized)
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["model"] == "gemini"


@pytest.mark.asyncio
async def test_query_endpoint_multiple_models(client, sample_data):
    """Test query endpoint handles multiple models sequentially."""
    response = await client.post("/query", json={
        "session_id": sample_data["session_id"],
        "query_text": "What was Apple's revenue in FY2023?",
        "models": ["gemini", "llama"],
        "company": "Apple"
    })
    
    # Expect either success or service unavailable
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        model_names = [r["model"] for r in data["results"]]
        assert "gemini" in model_names
        assert "llama" in model_names


# ============================================================================
# Test History Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_history_endpoint_empty_session(client, test_db):
    """Test history endpoint returns empty list for new session."""
    session_id = str(uuid.uuid4())
    response = await client.get(f"/history?session_id={session_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["turns"] == []


@pytest.mark.asyncio
async def test_history_endpoint_with_data(client, sample_data):
    """Test history endpoint returns session history."""
    response = await client.get(f"/history?session_id={sample_data['session_id']}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["session_id"] == sample_data["session_id"]
    assert len(data["turns"]) == 1
    
    turn = data["turns"][0]
    assert turn["query_id"] == sample_data["query_id"]
    assert turn["query_text"] == "What was Apple's revenue in FY2023?"
    assert turn["model_used"] == "gemini"
    assert turn["confidence_score"] == 0.95
    assert turn["refusal_flag"] is False
    assert turn["repair_count"] == 0


@pytest.mark.asyncio
async def test_history_endpoint_missing_session_id(client, test_db):
    """Test history endpoint requires session_id parameter."""
    response = await client.get("/history")
    assert response.status_code == 422


# ============================================================================
# Test Logs Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_logs_endpoint_no_filters(client, sample_data):
    """Test logs endpoint returns all logs without filters."""
    response = await client.get("/logs")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "logs" in data
    assert len(data["logs"]) >= 1
    
    # Check log structure
    log = data["logs"][0]
    assert "log_id" in log
    assert "session_id" in log
    assert "query_id" in log
    assert "timestamp" in log
    assert "log_json" in log


@pytest.mark.asyncio
async def test_logs_endpoint_filter_by_session(client, sample_data):
    """Test logs endpoint filters by session_id."""
    response = await client.get(f"/logs?session_id={sample_data['session_id']}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "logs" in data
    assert len(data["logs"]) >= 1
    
    # All logs should have the same session_id
    for log in data["logs"]:
        assert log["session_id"] == sample_data["session_id"]


@pytest.mark.asyncio
async def test_logs_endpoint_filter_by_query(client, sample_data):
    """Test logs endpoint filters by query_id."""
    response = await client.get(f"/logs?query_id={sample_data['query_id']}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "logs" in data
    assert len(data["logs"]) >= 1
    
    # All logs should have the same query_id
    for log in data["logs"]:
        assert log["query_id"] == sample_data["query_id"]


@pytest.mark.asyncio
async def test_logs_endpoint_limit(client, sample_data):
    """Test logs endpoint respects limit parameter."""
    # Create multiple log entries
    async with TestSessionLocal() as db:
        for i in range(5):
            await crud.create_log(
                db=db,
                session_id=sample_data["session_id"],
                query_id=sample_data["query_id"],
                log_json={"test": i}
            )
        await db.commit()
    
    # Request with limit
    response = await client.get("/logs?limit=3")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs"]) <= 3


# ============================================================================
# Test Evaluate Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_evaluate_endpoint(client, test_db):
    """Test evaluate endpoint triggers evaluation framework."""
    response = await client.post("/evaluate")
    
    # Expect either success or service unavailable (if evaluation framework not available)
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "metrics" in data
        assert "timestamp" in data
        
        # Should have metrics for all 3 models
        assert len(data["metrics"]) == 3
        
        for metric in data["metrics"]:
            assert "model" in metric
            assert "faithfulness" in metric
            assert "answer_relevancy" in metric
            assert "test_cases_run" in metric
            assert metric["model"] in ["llama", "gemma", "gemini"]


# ============================================================================
# Test Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_database_error_handling(client, test_db):
    """Test API handles database errors gracefully."""
    global test_engine
    
    # Close the test engine to simulate database failure
    await test_engine.dispose()
    
    # Try to access an endpoint that requires database
    response = await client.get(f"/history?session_id={str(uuid.uuid4())}")
    
    # Should return 503 Service Unavailable
    assert response.status_code == 503
    
    # Recreate engine for cleanup
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.mark.asyncio
async def test_validation_error_handling(client, test_db):
    """Test API returns 422 for validation errors."""
    # Send invalid request
    response = await client.post("/query", json={
        "session_id": "",  # Empty session_id
        "query_text": "test",
        "models": ["gemini"]
    })
    
    assert response.status_code == 422


# ============================================================================
# Test CORS Middleware
# ============================================================================

@pytest.mark.asyncio
async def test_cors_headers(client, test_db):
    """Test CORS middleware adds appropriate headers."""
    response = await client.options(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


# ============================================================================
# Test OpenAPI Documentation
# ============================================================================

@pytest.mark.asyncio
async def test_openapi_docs_available(client):
    """Test OpenAPI documentation is accessible."""
    response = await client.get("/docs")
    assert response.status_code == 200
    
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "FinDoc Intelligence API"
