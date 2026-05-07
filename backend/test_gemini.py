"""
Simple Gemini API test script.
Tests if your Gemini API key is working.
"""

import os
from dotenv import load_dotenv
from litellm import completion

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ No GEMINI_API_KEY found in .env file")
    exit(1)

print(f"🔑 Using API key: {api_key[:20]}...")

# Test with a simple question
try:
    print("\n🧪 Testing Gemini API with a simple question...")
    
    response = completion(
        model="gemini/gemini-2.5-flash",
        messages=[{"role": "user", "content": "What is 2+2? Answer with just the number."}],
        api_key=api_key
    )
    
    answer = response.choices[0].message.content
    
    print(f"\n✅ SUCCESS! Gemini responded:")
    print(f"   Answer: {answer}")
    print(f"\n🎉 Your Gemini API key is working!")
    
except Exception as e:
    error_msg = str(e)
    print(f"\n❌ FAILED! Error: {error_msg}")
    
    if "429" in error_msg or "quota" in error_msg.lower():
        print(f"\n💡 Rate limit or quota exceeded!")
        print(f"   - Free tier: 15 requests/minute, 1500 requests/day")
        print(f"   - Wait 1 minute and try again")
        print(f"   - Or get a new API key: https://aistudio.google.com/apikey")
    elif "403" in error_msg or "invalid" in error_msg.lower():
        print(f"\n💡 Invalid API key!")
        print(f"   - Get a new key: https://aistudio.google.com/apikey")
    else:
        print(f"\n💡 Check your API key at: https://aistudio.google.com/apikey")
    
    exit(1)
