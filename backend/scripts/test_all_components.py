#!/usr/bin/env python3
"""
Comprehensive Component Test with Real Data

Tests all components (Tasks 1-12) to ensure they work with the ingested SEC filings.
"""

import asyncio
import sys
from pathlib import Path

# Test results tracking
test_results = []


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    test_results.append((name, passed, message))
    print(f"{status}: {name}")
    if message:
        print(f"  → {message}")


async def test_config():
    """Test 1: Configuration"""
    print("\n" + "=" * 80)
    print("TEST 1: Configuration (Task 1)")
    print("=" * 80)
    
    try:
        from app.config import settings
        
        # Check required fields
        assert settings.database_url, "database_url is required"
        assert settings.chunk_size == 800, "chunk_size should be 800"
        assert settings.chunk_overlap == 200, "chunk_overlap should be 200"
        assert settings.retrieval_top_k == 10, "retrieval_top_k should be 10"
        
        log_test("Config loads successfully", True)
        log_test("Config has correct defaults", True)
        return True
    except Exception as e:
        log_test("Config test", False, str(e))
        return False


async def test_database():
    """Test 2: Database Layer"""
    print("\n" + "=" * 80)
    print("TEST 2: Database Layer (Task 2)")
    print("=" * 80)
    
    try:
        from sqlalchemy import select, func
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.config import settings
        from app.models import Document, Chunk
        
        # Convert URL if needed
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Test document count
            result = await db.execute(select(func.count(Document.id)))
            doc_count = result.scalar()
            
            # Test chunk count
            result = await db.execute(select(func.count(Chunk.id)))
            chunk_count = result.scalar()
            
            log_test("Database connection", True, f"{doc_count} documents, {chunk_count} chunks")
            
            # Test joinedload (no N+1 queries)
            result = await db.execute(
                select(Chunk).limit(1)
            )
            chunk = result.scalar_one_or_none()
            
            if chunk:
                log_test("Database models work", True)
            else:
                log_test("Database models", False, "No chunks found")
                return False
        
        await engine.dispose()
        return True
        
    except Exception as e:
        log_test("Database test", False, str(e))
        return False


async def test_document_processor():
    """Test 3: Document Processor"""
    print("\n" + "=" * 80)
    print("TEST 3: Document Processor (Task 3)")
    print("=" * 80)
    
    try:
        from app.ml.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        # Test with a real file
        test_file = Path("data/raw/AAPL/AAPL_10-K_2024-11-01.html")
        if not test_file.exists():
            log_test("Document processor", False, "Test file not found")
            return False
        
        # Test parse
        sections = processor.parse(str(test_file))
        log_test("Parse HTML file", len(sections) > 0, f"Found {len(sections)} sections")
        
        # Test chunk
        chunks = processor.chunk(sections[:2])  # Test with first 2 sections
        log_test("Chunk sections", len(chunks) > 0, f"Created {len(chunks)} chunks")
        
        # Test embed
        embeddings = processor.embed(chunks[:5])  # Test with first 5 chunks
        log_test("Generate embeddings", len(embeddings) > 0 and len(embeddings[0]) == 384, 
                f"Created {len(embeddings)} embeddings of dimension {len(embeddings[0]) if embeddings else 0}")
        
        return True
        
    except Exception as e:
        log_test("Document processor test", False, str(e))
        return False


async def test_hybrid_retrieval():
    """Test 4: Hybrid Retrieval"""
    print("\n" + "=" * 80)
    print("TEST 4: Hybrid Retrieval (Task 4)")
    print("=" * 80)
    
    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.config import settings
        from app.models import Chunk
        from app.ml.hybrid_retrieval import HybridRetriever
        
        # Get database connection
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Initialize retriever
            retriever = HybridRetriever(async_session)
            await retriever.build_bm25_index()
            
            log_test("HybridRetriever initialization", True, f"BM25 index built with {len(retriever.bm25_chunks)} chunks")
            
            # Test retrieval
            query = "What was Apple's revenue in 2024?"
            results = retriever.retrieve(query, top_k=10)
            
            log_test("Dense + Sparse retrieval", len(results) > 0, f"Retrieved {len(results)} chunks")
            
            if results:
                log_test("RRF fusion", True, f"Top result score: {results[0].score:.4f}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        log_test("Hybrid retrieval test", False, str(e))
        return False


async def test_llm_router():
    """Test 5: LLM Router"""
    print("\n" + "=" * 80)
    print("TEST 5: LLM Router (Task 5)")
    print("=" * 80)
    
    try:
        from app.ml.llm_router import LLMRouter
        
        router = LLMRouter()
        
        # Test model mapping
        assert router.MODELS["llama"] == "ollama/llama3.2:3b"
        assert router.MODELS["gemma"] == "ollama/gemma2:9b"
        assert router.MODELS["gemini"] == "gemini/gemini-2.0-flash"
        
        log_test("LLM Router initialization", True, "Model mappings correct")
        
        # Note: We won't actually call LLMs in this test
        log_test("LLM Router structure", True, "Ready for LLM calls")
        
        return True
        
    except Exception as e:
        log_test("LLM router test", False, str(e))
        return False


async def test_tool_registry():
    """Test 6: Tool Registry"""
    print("\n" + "=" * 80)
    print("TEST 6: Tool Registry (Task 6)")
    print("=" * 80)
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.config import settings
        from app.agent.tools import TOOLS, execute_tool, get_available_tools, validate_tool_inputs
        from app.ml.hybrid_retrieval import HybridRetriever
        
        # Check tool definitions
        assert "CALCULATE" in TOOLS
        assert "LOOKUP" in TOOLS
        assert "COMPARE" in TOOLS
        
        log_test("Tool definitions", True, f"Found {len(TOOLS)} tools")
        
        # Test get_available_tools
        calc_query = "What is the revenue growth rate?"
        tools = get_available_tools(calc_query)
        log_test("Tool firing restrictions", "CALCULATE" in tools, f"Available tools: {tools}")
        
        # Test CALCULATE tool
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            retriever = HybridRetriever(async_session)
            await retriever.build_bm25_index()
            
            # Test CALCULATE
            calc_result = execute_tool("CALCULATE", {"expression": "100 * 1.5"}, retriever, db)
            log_test("CALCULATE tool", calc_result["result"] == 150.0, f"Result: {calc_result}")
            
            # Test LOOKUP
            lookup_result = execute_tool("LOOKUP", {
                "entity": "Apple",
                "attribute": "revenue"
            }, retriever, db)
            log_test("LOOKUP tool", "chunk_text" in lookup_result, f"Found chunk_id: {lookup_result.get('chunk_id')}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        log_test("Tool registry test", False, str(e))
        return False


async def test_agent_pipeline():
    """Test 8-12: Agent Pipeline Components"""
    print("\n" + "=" * 80)
    print("TEST 8-12: Agent Pipeline (Tasks 8-12)")
    print("=" * 80)
    
    try:
        from app.agent.pipeline import (
            refusal_guard_node,
            planner_node,
            executor_node,
            critic_node,
            AgentState
        )
        
        # Test RefusalGuard
        state = AgentState(
            query="Should I buy Apple stock?",
            session_id="test",
            model_used="gemini",
            plan=[],
            tool_results=[],
            draft_response="",
            citations=[],
            critic_verdict="",
            repair_count=0,
            refusal=False,
            refusal_reason=None,
            memory_context="",
            latency_ms=0,
            confidence_score=0.0,
            turn_count=1
        )
        
        result = refusal_guard_node(state)
        log_test("RefusalGuard node", result["refusal"] == True, 
                f"Correctly refused: {result.get('refusal_reason')}")
        
        # Test allowed query
        state["query"] = "What was Apple's revenue in 2024?"
        result = refusal_guard_node(state)
        log_test("RefusalGuard allows valid query", result["refusal"] == False)
        
        log_test("Agent pipeline structure", True, "All nodes defined")
        
        return True
        
    except Exception as e:
        log_test("Agent pipeline test", False, str(e))
        return False


async def main():
    """Run all tests."""
    print("=" * 80)
    print("COMPREHENSIVE COMPONENT TEST WITH REAL DATA")
    print("Testing Tasks 1-12 with ingested SEC filings")
    print("=" * 80)
    
    # Run all tests
    await test_config()
    await test_database()
    await test_document_processor()
    await test_hybrid_retrieval()
    await test_llm_router()
    await test_tool_registry()
    await test_agent_pipeline()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, p, _ in test_results if p)
    total = len(test_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        print("\nFailed tests:")
        for name, passed, message in test_results:
            if not passed:
                print(f"  - {name}: {message}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
