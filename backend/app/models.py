"""
SQLAlchemy ORM models for FinDoc Intelligence.

This module defines all database tables matching the schema in the design document:
- documents: SEC filing metadata
- chunks: Text segments from documents
- queries: User queries
- responses: Agent-generated responses
- citations: Links between responses and source chunks
- memory_summaries: Session context and turn summaries
- logs: Structured agent execution logs
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    """
    SEC filing documents (10-K, 10-Q).
    
    Stores metadata about ingested financial documents.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False, index=True)
    filing_type = Column(String, nullable=False)  # "10-K" or "10-Q"
    fiscal_year = Column(Integer, nullable=False, index=True)
    filing_date = Column(Date, nullable=False)
    source_url = Column(String, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """
    Text chunks from documents with metadata.
    
    Each chunk is a segment of a document with preserved section and page information.
    """
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    section_label = Column(String, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    citations = relationship("Citation", back_populates="chunk", cascade="all, delete-orphan")


class Query(Base):
    """
    User queries submitted to the system.
    
    Tracks all questions asked within sessions.
    """
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    model_used = Column(String, nullable=False)
    
    # Relationships
    responses = relationship("Response", back_populates="query", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="query", cascade="all, delete-orphan")


class Response(Base):
    """
    Agent-generated responses to queries.
    
    Stores the final answer with metadata about confidence, refusals, and repair iterations.
    """
    __tablename__ = "responses"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    response_text = Column(Text, nullable=False)
    model_used = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    refusal_flag = Column(Boolean, nullable=False, default=False)
    refusal_reason = Column(String, nullable=True)
    repair_count = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    query = relationship("Query", back_populates="responses")
    citations = relationship("Citation", back_populates="response", cascade="all, delete-orphan")


class Citation(Base):
    """
    Links between responses and source chunks.
    
    Provides grounding for factual claims in responses.
    """
    __tablename__ = "citations"
    
    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    relevance_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    response = relationship("Response", back_populates="citations")
    chunk = relationship("Chunk", back_populates="citations")


class MemorySummary(Base):
    """
    Session memory summaries and raw turns.
    
    Stores both individual turn records and compressed summaries for context management.
    """
    __tablename__ = "memory_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    turn_range_start = Column(Integer, nullable=False)
    turn_range_end = Column(Integer, nullable=False)
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Log(Base):
    """
    Structured logs of agent execution.
    
    Stores complete execution traces for debugging and auditing.
    """
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    log_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    query = relationship("Query", back_populates="logs")


class EvaluationResult(Base):
    """
    Per-case evaluation results with Ragas metrics.
    
    Stores individual test case evaluation results for each model.
    """
    __tablename__ = "evaluation_results"
    
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String, nullable=False, index=True)
    model_used = Column(String, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    faithfulness = Column(Float, nullable=False)
    answer_relevancy = Column(Float, nullable=False)
    refusal_flag = Column(Boolean, nullable=False, default=False)
    expected_refusal = Column(Boolean, nullable=False, default=False)
    refusal_correct = Column(Boolean, nullable=False, default=True)
    latency_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class EvaluationAggregate(Base):
    """
    Aggregate evaluation metrics per model.
    
    Stores mean Faithfulness and AnswerRelevancy across all test cases for each model.
    """
    __tablename__ = "evaluation_aggregates"
    
    id = Column(Integer, primary_key=True, index=True)
    model_used = Column(String, nullable=False, index=True)
    mean_faithfulness = Column(Float, nullable=False)
    mean_answer_relevancy = Column(Float, nullable=False)
    test_cases_count = Column(Integer, nullable=False)
    refusal_accuracy = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
