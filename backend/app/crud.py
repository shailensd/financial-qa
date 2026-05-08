"""
CRUD operations for FinDoc Intelligence.

All functions use joinedload to prevent N+1 query issues when accessing
foreign key relationships.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from datetime import datetime

from app.models import (
    Document,
    Chunk,
    Query,
    Response,
    Citation,
    MemorySummary,
    Log,
)


# ============================================================================
# Document Operations
# ============================================================================

async def create_document(
    db: AsyncSession,
    company: str,
    filing_type: str,
    fiscal_year: int,
    filing_date: datetime,
    source_url: str,
    metadata_json: Optional[dict] = None,
) -> Document:
    """
    Create a new document record.
    
    Args:
        db: Database session
        company: Company name
        filing_type: Type of filing (10-K, 10-Q)
        fiscal_year: Fiscal year
        filing_date: Date of filing
        source_url: URL to source document
        metadata_json: Optional additional metadata
    
    Returns:
        Created Document instance
    """
    document = Document(
        company=company,
        filing_type=filing_type,
        fiscal_year=fiscal_year,
        filing_date=filing_date,
        source_url=source_url,
        metadata_json=metadata_json or {},
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


# ============================================================================
# Chunk Operations
# ============================================================================

async def create_chunk(
    db: AsyncSession,
    document_id: int,
    chunk_text: str,
    chunk_index: int,
    section_label: Optional[str] = None,
    page_number: Optional[int] = None,
) -> Chunk:
    """
    Create a new chunk record.
    
    Args:
        db: Database session
        document_id: Foreign key to documents table
        chunk_text: Text content of the chunk
        chunk_index: Position of chunk within document
        section_label: Optional section label (e.g., "Item 7. MD&A")
        page_number: Optional page number
    
    Returns:
        Created Chunk instance with document relationship loaded
    """
    chunk = Chunk(
        document_id=document_id,
        chunk_text=chunk_text,
        chunk_index=chunk_index,
        section_label=section_label,
        page_number=page_number,
    )
    db.add(chunk)
    await db.flush()
    await db.refresh(chunk, ["document"])
    return chunk


# ============================================================================
# Query Operations
# ============================================================================

async def create_query(
    db: AsyncSession,
    session_id: str,
    query_text: str,
    model_used: str,
) -> Query:
    """
    Create a new query record.
    
    Args:
        db: Database session
        session_id: Session identifier
        query_text: User's query text
        model_used: Model used for this query
    
    Returns:
        Created Query instance
    """
    query = Query(
        session_id=session_id,
        query_text=query_text,
        model_used=model_used,
    )
    db.add(query)
    await db.flush()
    await db.refresh(query)
    return query


# ============================================================================
# Response Operations
# ============================================================================

async def create_response(
    db: AsyncSession,
    query_id: int,
    response_text: str,
    model_used: str,
    confidence_score: float,
    latency_ms: int,
    refusal_flag: bool = False,
    refusal_reason: Optional[str] = None,
    repair_count: int = 0,
) -> Response:
    """
    Create a new response record.
    
    Args:
        db: Database session
        query_id: Foreign key to queries table
        response_text: Generated response text
        model_used: Model used for generation
        confidence_score: Confidence score (0.0-1.0)
        latency_ms: Response latency in milliseconds
        refusal_flag: Whether the query was refused
        refusal_reason: Reason for refusal if applicable
        repair_count: Number of repair iterations
    
    Returns:
        Created Response instance with query relationship loaded
    """
    response = Response(
        query_id=query_id,
        response_text=response_text,
        model_used=model_used,
        confidence_score=confidence_score,
        latency_ms=latency_ms,
        refusal_flag=refusal_flag,
        refusal_reason=refusal_reason,
        repair_count=repair_count,
    )
    db.add(response)
    await db.flush()
    await db.refresh(response, ["query"])
    return response


# ============================================================================
# Citation Operations
# ============================================================================

async def create_citation(
    db: AsyncSession,
    response_id: int,
    chunk_id: int,
    relevance_score: float,
) -> Citation:
    """
    Create a new citation record.
    
    Args:
        db: Database session
        response_id: Foreign key to responses table
        chunk_id: Foreign key to chunks table
        relevance_score: Relevance score for this citation
    
    Returns:
        Created Citation instance with response and chunk relationships loaded
    """
    citation = Citation(
        response_id=response_id,
        chunk_id=chunk_id,
        relevance_score=relevance_score,
    )
    db.add(citation)
    await db.flush()
    await db.refresh(citation, ["response", "chunk"])
    return citation


# ============================================================================
# Memory Operations
# ============================================================================

async def write_memory(
    db: AsyncSession,
    session_id: str,
    turn_range_start: int,
    turn_range_end: int,
    summary_text: str,
) -> MemorySummary:
    """
    Write a memory summary entry.
    
    Args:
        db: Database session
        session_id: Session identifier
        turn_range_start: Starting turn number
        turn_range_end: Ending turn number
        summary_text: Summary text content
    
    Returns:
        Created MemorySummary instance
    """
    memory = MemorySummary(
        session_id=session_id,
        turn_range_start=turn_range_start,
        turn_range_end=turn_range_end,
        summary_text=summary_text,
    )
    db.add(memory)
    await db.flush()
    await db.refresh(memory)
    return memory


async def get_recent_memory(
    db: AsyncSession,
    session_id: str,
    limit: int = 1,
) -> List[MemorySummary]:
    """
    Get the most recent memory summaries for a session.
    
    Args:
        db: Database session
        session_id: Session identifier
        limit: Number of recent summaries to retrieve
    
    Returns:
        List of MemorySummary instances ordered by id descending (most recent first)
    """
    stmt = (
        select(MemorySummary)
        .where(MemorySummary.session_id == session_id)
        .order_by(desc(MemorySummary.id))  # Use id for deterministic ordering
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_raw_turns(
    db: AsyncSession,
    session_id: str,
    limit: int = 2,
) -> List[tuple[Query, Response]]:
    """
    Get the most recent raw query-response turns for a session.
    
    Args:
        db: Database session
        session_id: Session identifier
        limit: Number of recent turns to retrieve
    
    Returns:
        List of (Query, Response) tuples ordered by query id descending (most recent first)
    """
    stmt = (
        select(Query, Response)
        .join(Response, Query.id == Response.query_id)
        .where(Query.session_id == session_id)
        .order_by(desc(Query.id))  # Use id for deterministic ordering
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.all())


async def get_session_history(
    db: AsyncSession,
    session_id: str,
) -> List[tuple[Query, Response]]:
    """
    Get complete session history with all queries and responses.
    
    Uses joinedload to prevent N+1 queries when accessing relationships.
    
    Args:
        db: Database session
        session_id: Session identifier
    
    Returns:
        List of (Query, Response) tuples ordered by timestamp ascending
    """
    stmt = (
        select(Query)
        .options(joinedload(Query.responses))
        .where(Query.session_id == session_id)
        .order_by(Query.timestamp)
    )
    result = await db.execute(stmt)
    queries = result.unique().scalars().all()
    
    # Flatten to (Query, Response) tuples
    history = []
    for query in queries:
        for response in query.responses:
            history.append((query, response))
    
    return history


# ============================================================================
# Log Operations
# ============================================================================

async def create_log(
    db: AsyncSession,
    session_id: str,
    query_id: int,
    log_json: dict,
) -> Log:
    """
    Create a new structured log entry.
    
    Args:
        db: Database session
        session_id: Session identifier
        query_id: Foreign key to queries table
        log_json: Structured log data as dictionary
    
    Returns:
        Created Log instance with query relationship loaded
    """
    log = Log(
        session_id=session_id,
        query_id=query_id,
        log_json=log_json,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log, ["query"])
    return log


async def get_logs(
    db: AsyncSession,
    session_id: Optional[str] = None,
    query_id: Optional[int] = None,
    limit: int = 100,
) -> List[Log]:
    """
    Retrieve structured logs with optional filtering.
    
    Uses joinedload to prevent N+1 queries when accessing query relationship.
    
    Args:
        db: Database session
        session_id: Optional session filter
        query_id: Optional query filter
        limit: Maximum number of logs to retrieve
    
    Returns:
        List of Log instances ordered by created_at descending
    """
    stmt = select(Log).options(joinedload(Log.query))
    
    if session_id:
        stmt = stmt.where(Log.session_id == session_id)
    if query_id:
        stmt = stmt.where(Log.query_id == query_id)
    
    stmt = stmt.order_by(desc(Log.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


# ============================================================================
# Evaluation Operations
# ============================================================================

async def create_evaluation_result(
    db: AsyncSession,
    test_case_id: str,
    model_used: str,
    query_text: str,
    response_text: str,
    faithfulness: float,
    answer_relevancy: float,
    refusal_flag: bool,
    expected_refusal: bool,
    latency_ms: int,
) -> "EvaluationResult":
    """
    Create a new evaluation result record.
    
    Args:
        db: Database session
        test_case_id: Test case identifier
        model_used: Model used for evaluation
        query_text: Query text
        response_text: Generated response text
        faithfulness: Ragas faithfulness score
        answer_relevancy: Ragas answer relevancy score
        refusal_flag: Whether the query was refused
        expected_refusal: Whether refusal was expected
        latency_ms: Response latency in milliseconds
    
    Returns:
        Created EvaluationResult instance
    """
    from app.models import EvaluationResult
    
    refusal_correct = (refusal_flag == expected_refusal)
    
    result = EvaluationResult(
        test_case_id=test_case_id,
        model_used=model_used,
        query_text=query_text,
        response_text=response_text,
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        refusal_flag=refusal_flag,
        expected_refusal=expected_refusal,
        refusal_correct=refusal_correct,
        latency_ms=latency_ms,
    )
    db.add(result)
    await db.flush()
    await db.refresh(result)
    return result


async def create_evaluation_aggregate(
    db: AsyncSession,
    model_used: str,
    mean_faithfulness: float,
    mean_answer_relevancy: float,
    test_cases_count: int,
    refusal_accuracy: float,
) -> "EvaluationAggregate":
    """
    Create a new evaluation aggregate record.
    
    Args:
        db: Database session
        model_used: Model used for evaluation
        mean_faithfulness: Mean faithfulness score across all test cases
        mean_answer_relevancy: Mean answer relevancy score across all test cases
        test_cases_count: Number of test cases evaluated
        refusal_accuracy: Accuracy of refusal decisions (0.0-1.0)
    
    Returns:
        Created EvaluationAggregate instance
    """
    from app.models import EvaluationAggregate
    
    aggregate = EvaluationAggregate(
        model_used=model_used,
        mean_faithfulness=mean_faithfulness,
        mean_answer_relevancy=mean_answer_relevancy,
        test_cases_count=test_cases_count,
        refusal_accuracy=refusal_accuracy,
    )
    db.add(aggregate)
    await db.flush()
    await db.refresh(aggregate)
    return aggregate


async def get_evaluation_results(
    db: AsyncSession,
    model_used: Optional[str] = None,
    test_case_id: Optional[str] = None,
    limit: int = 100,
) -> List["EvaluationResult"]:
    """
    Retrieve evaluation results with optional filtering.
    
    Args:
        db: Database session
        model_used: Optional model filter
        test_case_id: Optional test case filter
        limit: Maximum number of results to retrieve
    
    Returns:
        List of EvaluationResult instances ordered by created_at descending
    """
    from app.models import EvaluationResult
    
    stmt = select(EvaluationResult)
    
    if model_used:
        stmt = stmt.where(EvaluationResult.model_used == model_used)
    if test_case_id:
        stmt = stmt.where(EvaluationResult.test_case_id == test_case_id)
    
    stmt = stmt.order_by(desc(EvaluationResult.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_evaluation_aggregates(
    db: AsyncSession,
    model_used: Optional[str] = None,
    limit: int = 10,
) -> List["EvaluationAggregate"]:
    """
    Retrieve evaluation aggregates with optional filtering.
    
    Args:
        db: Database session
        model_used: Optional model filter
        limit: Maximum number of aggregates to retrieve
    
    Returns:
        List of EvaluationAggregate instances ordered by created_at descending
    """
    from app.models import EvaluationAggregate
    
    stmt = select(EvaluationAggregate)
    
    if model_used:
        stmt = stmt.where(EvaluationAggregate.model_used == model_used)
    
    stmt = stmt.order_by(desc(EvaluationAggregate.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())
