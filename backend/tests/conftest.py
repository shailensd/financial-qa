import os
import pytest

# Ensure required environment variables are set before any tests import app modules
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GEMINI_API_KEY", "dummy_test_key_for_gemini_api")
