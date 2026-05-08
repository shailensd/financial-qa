"""
FastAPI application for FinDoc Intelligence.

This module provides the complete REST API for the financial Q&A system,
including query processing, session history, evaluation, health checks, and logging.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, engine, Base, SessionLocal
from app.ml.hybrid_retrieval import HybridRetriever
from app.agent.pipeline import run_agent_pipeline
from app import crud


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global instances initialized at startup
hybrid_retriever: Optional[HybridRetriever] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown operations:
    - Startup: Initialize database, ChromaDB, and BM25 index
    - Shutdown: Clean up resources
    """
    logger.info("Starting FinDoc Intelligence API...")
    
    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize hybrid retriever with BM25 index
    global hybrid_retriever
    try:
        hybrid_retriever = HybridRetriever(db_session_factory=SessionLocal)
        await hybrid_retriever.build_bm25_index()
        logger.info("Hybrid retriever initialized with BM25 index")
    except Exception as e:
        logger.error(f"Failed to initialize hybrid retriever: {e}")
        # Continue without retriever - will fail gracefully on queries
        hybrid_retriever = None
    
    logger.info("FinDoc Intelligence API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FinDoc Intelligence API...")
    await engine.dispose()
    logger.info("FinDoc Intelligence API shut down")


# Create FastAPI app
app = FastAPI(
    title="FinDoc Intelligence API",
    description="Financial Q&A system with RAG and Planner-Executor-Critic agent pipeline",
    version="1.0.0",
    lifespan=lifespan
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request model for POST /query endpoint."""
    session_id: str = Field(..., min_length=1, max_length=100, description="Session identifier")
    query_text: str = Field(..., min_length=3, max_length=1000, description="User's query text")
    models: List[str] = Field(..., min_length=1, max_length=3, description="List of models to use (llama, gemma, gemini)")
    company: Optional[str] = Field(None, max_length=50, description="Optional company filter")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "query_text": "What was Apple's revenue in FY2023?",
                "models": ["gemini"],
                "company": "Apple"
            }
        }
    }


class CitationResponse(BaseModel):
    """Citation object in response."""
    chunk_id: int
    chunk_text: str
    relevance_score: float


class AgentTraceResponse(BaseModel):
    """Agent execution trace in response."""
    plan: List[dict]
    tool_results: List[dict]
    critic_verdict: str


class ModelResponse(BaseModel):
    """Response from a single model."""
    model: str
    response_text: str
    confidence_score: float
    refusal_flag: bool
    refusal_reason: Optional[str]
    repair_count: int
    citations: List[CitationResponse]
    agent_trace: AgentTraceResponse
    latency_ms: int


class QueryResponse(BaseModel):
    """Response model for POST /query endpoint."""
    results: List[ModelResponse]


class HistoryTurn(BaseModel):
    """Single turn in session history."""
    query_id: int
    query_text: str
    timestamp: str
    model_used: str
    response_text: str
    confidence_score: float
    refusal_flag: bool
    repair_count: int


class HistoryResponse(BaseModel):
    """Response model for GET /history endpoint."""
    session_id: str
    turns: List[HistoryTurn]


class HealthResponse(BaseModel):
    """Response model for GET /health endpoint."""
    status: str
    db: str
    chroma: str
    bm25: str


class LogEntry(BaseModel):
    """Single log entry."""
    log_id: int
    session_id: str
    query_id: int
    timestamp: str
    log_json: dict


class LogsResponse(BaseModel):
    """Response model for GET /logs endpoint."""
    logs: List[LogEntry]


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for a single model."""
    model: str
    faithfulness: float
    answer_relevancy: float
    test_cases_run: int


class EvaluationResponse(BaseModel):
    """Response model for POST /evaluate endpoint."""
    metrics: List[EvaluationMetrics]
    timestamp: str


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred"}
    )


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Checks the status of:
    - Database connection
    - ChromaDB availability
    - BM25 index availability
    
    Returns:
        HealthResponse with status of each component
    """
    # Check database connection
    db_status = "disconnected"
    try:
        # Simple query to verify connection
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Check ChromaDB availability
    chroma_status = "unavailable"
    if hybrid_retriever and hybrid_retriever.chroma_available:
        chroma_status = "connected"
    
    # Check BM25 index availability
    bm25_status = "unavailable"
    if hybrid_retriever and hybrid_retriever.bm25_index is not None:
        bm25_status = "ready"
    
    # Determine overall status
    overall_status = "ok" if db_status == "connected" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        db=db_status,
        chroma=chroma_status,
        bm25=bm25_status
    )


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_endpoint(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a query through the agent pipeline.
    
    Validates the request, runs the agent pipeline for each requested model
    sequentially, and returns multi-model response array.
    
    Args:
        request: QueryRequest with session_id, query_text, models, and optional company
        db: Database session dependency
    
    Returns:
        QueryResponse with results from each model
    
    Raises:
        HTTPException 503: If database is unavailable
        HTTPException 504: If LLM timeout occurs
        HTTPException 422: If validation fails
    """
    # Validate models
    valid_models = {"llama", "gemma", "gemini"}
    invalid_models = set(request.models) - valid_models
    if invalid_models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid models: {invalid_models}. Valid models: {valid_models}"
        )
    
    # Check if retriever is available
    if hybrid_retriever is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval system is not available"
        )
    
    results = []
    
    # Execute query for each model sequentially
    for model in request.models:
        try:
            logger.info(
                f"Processing query for model={model}, session={request.session_id}, "
                f"query={request.query_text[:50]}..."
            )
            
            # Run agent pipeline
            result = await run_agent_pipeline(
                query=request.query_text,
                session_id=request.session_id,
                model_used=model,
                db=db,
                retriever=hybrid_retriever,
                db_session_factory=SessionLocal,
                ollama_base_url=settings.ollama_base_url,
                gemini_api_key=settings.gemini_api_key,
                groq_api_key=settings.groq_api_key,
                company=request.company,
            )
            
            # Build citations with chunk text
            citations = []
            for citation in result.get("citations", []):
                chunk_id = citation.get("chunk_id")
                relevance_score = citation.get("relevance_score", 0.9)
                
                # Fetch chunk text from database
                chunk_text = ""
                try:
                    from sqlalchemy import select
                    from app.models import Chunk
                    stmt = select(Chunk).where(Chunk.id == chunk_id)
                    chunk_result = await db.execute(stmt)
                    chunk = chunk_result.scalar_one_or_none()
                    if chunk:
                        chunk_text = chunk.chunk_text
                except Exception as e:
                    logger.error(f"Failed to fetch chunk {chunk_id}: {e}")
                
                citations.append(CitationResponse(
                    chunk_id=chunk_id,
                    chunk_text=chunk_text,
                    relevance_score=relevance_score
                ))
            
            # Build model response
            model_response = ModelResponse(
                model=model,
                response_text=result.get("response_text", ""),
                confidence_score=result.get("confidence_score", 0.0),
                refusal_flag=result.get("refusal_flag", False),
                refusal_reason=result.get("refusal_reason"),
                repair_count=result.get("repair_count", 0),
                citations=citations,
                agent_trace=AgentTraceResponse(
                    plan=result.get("agent_trace", {}).get("plan", []),
                    tool_results=result.get("agent_trace", {}).get("tool_results", []),
                    critic_verdict=result.get("agent_trace", {}).get("critic_verdict", "unknown")
                ),
                latency_ms=result.get("latency_ms", 0)
            )
            
            results.append(model_response)
            
            logger.info(
                f"Query processed successfully for model={model}, "
                f"latency={result.get('latency_ms')}ms"
            )
        
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        
        except Exception as e:
            logger.error(f"Query processing failed for model={model}: {e}", exc_info=True)
            
            # Check for specific error types
            if "timeout" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"LLM timeout for model {model}"
                )
            
            # Return error response for this model but continue with others
            results.append(ModelResponse(
                model=model,
                response_text=f"Error: {str(e)}",
                confidence_score=0.0,
                refusal_flag=False,
                refusal_reason=None,
                repair_count=0,
                citations=[],
                agent_trace=AgentTraceResponse(
                    plan=[],
                    tool_results=[],
                    critic_verdict="error"
                ),
                latency_ms=0
            ))
    
    return QueryResponse(results=results)


@app.get("/history", response_model=HistoryResponse, tags=["Session"])
async def get_history(
    session_id: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get session history with all queries and responses.
    
    Args:
        session_id: Session identifier
        db: Database session dependency
    
    Returns:
        HistoryResponse with ordered list of query-response turns
    
    Raises:
        HTTPException 503: If database is unavailable
    """
    try:
        # Fetch session history from database
        history = await crud.get_session_history(db, session_id)
        
        # Build response
        turns = []
        for query, response in history:
            turns.append(HistoryTurn(
                query_id=query.id,
                query_text=query.query_text,
                timestamp=query.timestamp.isoformat(),
                model_used=response.model_used,
                response_text=response.response_text,
                confidence_score=response.confidence_score,
                refusal_flag=response.refusal_flag,
                repair_count=response.repair_count
            ))
        
        logger.info(f"Retrieved {len(turns)} turns for session {session_id}")
        
        return HistoryResponse(
            session_id=session_id,
            turns=turns
        )
    
    except Exception as e:
        logger.error(f"Failed to retrieve history for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve session history"
        )


@app.get("/logs", response_model=LogsResponse, tags=["Logging"])
async def get_logs(
    session_id: Optional[str] = Query(None),
    query_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Get structured logs with optional filtering.
    
    Args:
        session_id: Optional session filter
        query_id: Optional query filter
        limit: Maximum number of logs to return (1-1000)
        db: Database session dependency
    
    Returns:
        LogsResponse with list of log entries
    
    Raises:
        HTTPException 503: If database is unavailable
    """
    try:
        # Fetch logs from database
        logs = await crud.get_logs(
            db=db,
            session_id=session_id,
            query_id=query_id,
            limit=limit
        )
        
        # Build response
        log_entries = []
        for log in logs:
            log_entries.append(LogEntry(
                log_id=log.id,
                session_id=log.session_id,
                query_id=log.query_id,
                timestamp=log.created_at.isoformat(),
                log_json=log.log_json
            ))
        
        logger.info(
            f"Retrieved {len(log_entries)} logs "
            f"(session_id={session_id}, query_id={query_id})"
        )
        
        return LogsResponse(logs=log_entries)
    
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve logs"
        )


@app.post("/evaluate", response_model=EvaluationResponse, tags=["Evaluation"])
async def evaluate_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Trigger evaluation framework for all models.
    
    Runs the evaluation framework with Ragas metrics (Faithfulness and Answer Relevancy)
    for all 3 models (llama, gemma, gemini) across the evaluation test set.
    
    Args:
        db: Database session dependency
    
    Returns:
        EvaluationResponse with metrics for each model
    
    Raises:
        HTTPException 503: If evaluation framework is unavailable
        HTTPException 500: If evaluation fails
    """
    try:
        # Import evaluation runner
        from backend.eval.runner import EvaluationRunner
        
        # Initialize evaluation runner
        runner = EvaluationRunner(db_session_factory=db)
        
        # Run evaluation for all models
        models = ["llama", "gemma", "gemini"]
        metrics_list = []
        
        for model in models:
            logger.info(f"Running evaluation for model={model}")
            
            try:
                # Run evaluation
                results = await runner.run(model=model)
                
                # Extract metrics
                metrics_list.append(EvaluationMetrics(
                    model=model,
                    faithfulness=results.get("faithfulness", 0.0),
                    answer_relevancy=results.get("answer_relevancy", 0.0),
                    test_cases_run=results.get("test_cases_run", 0)
                ))
                
                logger.info(
                    f"Evaluation completed for model={model}: "
                    f"faithfulness={results.get('faithfulness'):.3f}, "
                    f"answer_relevancy={results.get('answer_relevancy'):.3f}"
                )
            
            except Exception as e:
                logger.error(f"Evaluation failed for model={model}: {e}", exc_info=True)
                # Continue with other models
                metrics_list.append(EvaluationMetrics(
                    model=model,
                    faithfulness=0.0,
                    answer_relevancy=0.0,
                    test_cases_run=0
                ))
        
        from datetime import datetime, timezone
        return EvaluationResponse(
            metrics=metrics_list,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    except ImportError as e:
        logger.error(f"Evaluation framework not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evaluation framework is not available"
        )
    
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "FinDoc Intelligence API",
        "version": "1.0.0",
        "description": "Financial Q&A system with RAG and Planner-Executor-Critic agent pipeline",
        "docs": "/docs",
        "health": "/health"
    }
