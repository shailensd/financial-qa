#!/usr/bin/env python3
"""Test simple query through LiteLLM."""

import asyncio
from app.ml.llm_router import LLMRouter

async def test_llama():
    router = LLMRouter(
        ollama_base_url="http://localhost:11434",
        gemini_api_key="dummy"
    )
    
    messages = [{"role": "user", "content": "What is 2+2?"}]
    
    print("Testing Llama via LiteLLM...")
    try:
        response = router.complete(
            model="llama",
            messages=messages,
            temperature=0.0
        )
        print(f"✓ Success: {response}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llama())
