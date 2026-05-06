#!/usr/bin/env python3
"""
Quick test script to verify LLM connectivity.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini():
    """Test Gemini API connection."""
    from app.ml.llm_router import LLMRouter
    
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"Testing Gemini with API key: {api_key[:10]}..." if api_key else "No API key found")
    
    router = LLMRouter(
        ollama_base_url="http://localhost:11434",
        gemini_api_key=api_key
    )
    
    messages = [
        {"role": "user", "content": "What is 2+2? Answer with just the number."}
    ]
    
    try:
        response = router.complete(
            model="gemini",
            messages=messages,
            temperature=0.0
        )
        print(f"✓ Gemini works! Response: {response}")
        return True
    except Exception as e:
        print(f"✗ Gemini failed: {e}")
        return False


def test_ollama():
    """Test Ollama connection."""
    import requests
    
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json()
            print(f"✓ Ollama is running with {len(models.get('models', []))} models")
            return True
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Ollama not accessible: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Connectivity Test")
    print("=" * 60)
    print()
    
    print("1. Testing Ollama...")
    ollama_ok = test_ollama()
    print()
    
    print("2. Testing Gemini...")
    gemini_ok = test_gemini()
    print()
    
    print("=" * 60)
    if gemini_ok:
        print("✓ All tests passed! You're ready to go.")
    else:
        print("✗ Some tests failed. Check the errors above.")
    print("=" * 60)
