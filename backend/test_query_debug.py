"""
Debug script to test query execution and see detailed logs.
"""
import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.ml.hybrid_retrieval import HybridRetriever
from app.agent.pipeline import run_agent_pipeline
from app.database import SessionLocal

# Configure logging to see all debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

async def main():
    # Create database session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_factory() as db:
        # Initialize retriever
        retriever = HybridRetriever(
            db_session_factory=SessionLocal,
            chroma_persist_directory=settings.chroma_persist_dir,
            embedding_model_name=settings.embedding_model
        )
        
        # Run query
        print("\n" + "="*80)
        print("TESTING QUERY: What was Apple revenue in FY2023?")
        print("="*80 + "\n")
        
        result = await run_agent_pipeline(
            query="What was Apple revenue in FY2023?",
            session_id="test-debug-002",
            model_used="llama",
            db=db,
            retriever=retriever,
            ollama_base_url="http://localhost:11434",
            gemini_api_key=settings.gemini_api_key,
            company="Apple"
        )
        
        print("\n" + "="*80)
        print("RESULT:")
        print("="*80)
        print(f"Response: {result['response_text']}")
        print(f"Confidence: {result['confidence_score']}")
        print(f"Repair count: {result['repair_count']}")
        print(f"Refusal: {result['refusal_flag']}")
        print(f"Citations: {len(result['citations'])}")
        print(f"Latency: {result['latency_ms']}ms")
        print(f"\nAgent Trace:")
        print(f"  Plan: {result['agent_trace'].get('plan', [])}")
        print(f"  Tool results: {len(result['agent_trace'].get('tool_results', []))}")
        print(f"  Critic verdict: {result['agent_trace'].get('critic_verdict')}")
        
        # Print tool results in detail
        for i, tr in enumerate(result['agent_trace'].get('tool_results', [])):
            print(f"\n  Tool Result {i+1}:")
            print(f"    Tool: {tr.get('tool')}")
            print(f"    Status: {tr.get('status')}")
            print(f"    Output: {str(tr.get('output', ''))[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
