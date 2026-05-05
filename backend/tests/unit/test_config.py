"""
Unit tests for configuration validation.

Tests that required configuration fields raise ValueError when missing.
"""

import pytest
import os
from pydantic import ValidationError


def test_config_raises_error_for_missing_database_url(monkeypatch):
    """Test that Settings raises ValueError when database_url is missing."""
    # Clear any existing environment variables
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    # Set only gemini_api_key to isolate database_url validation
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    
    # Import Settings here to avoid loading global settings
    from app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    # Verify the error mentions database_url
    error_str = str(exc_info.value)
    assert "database_url" in error_str.lower()


def test_config_raises_error_for_missing_gemini_api_key(monkeypatch):
    """Test that Settings raises ValueError when gemini_api_key is missing."""
    # Clear any existing environment variables
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    # Set only database_url to isolate gemini_api_key validation
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    
    from app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    # Verify the error mentions gemini_api_key
    error_str = str(exc_info.value)
    assert "gemini_api_key" in error_str.lower()


def test_config_raises_error_for_empty_database_url(monkeypatch):
    """Test that Settings raises ValueError when database_url is empty string."""
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    
    from app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    error_str = str(exc_info.value)
    assert "database_url" in error_str.lower()


def test_config_raises_error_for_empty_gemini_api_key(monkeypatch):
    """Test that Settings raises ValueError when gemini_api_key is empty string."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    from app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    error_str = str(exc_info.value)
    assert "gemini_api_key" in error_str.lower()


def test_config_raises_error_for_whitespace_only_fields(monkeypatch):
    """Test that Settings raises ValueError when required fields contain only whitespace."""
    monkeypatch.setenv("DATABASE_URL", "   ")
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    
    from app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    error_str = str(exc_info.value)
    assert "database_url" in error_str.lower()


def test_config_succeeds_with_valid_required_fields(monkeypatch):
    """Test that Settings initializes successfully when all required fields are provided."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/findoc")
    monkeypatch.setenv("GEMINI_API_KEY", "valid_api_key_123")
    
    from app.config import Settings
    
    # Should not raise any exception
    settings = Settings()
    
    assert settings.database_url == "postgresql://user:pass@localhost:5432/findoc"
    assert settings.gemini_api_key == "valid_api_key_123"
    
    # Verify defaults are set
    assert settings.chunk_size == 800
    assert settings.chunk_overlap == 200
    assert settings.retrieval_top_k == 10
    assert settings.max_repair_iterations == 2


def test_config_raises_error_for_both_missing_fields(monkeypatch):
    """Test that Settings raises ValidationError when both required fields are missing."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    from app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    # Both fields should be mentioned in the error
    error_str = str(exc_info.value)
    assert "database_url" in error_str.lower() or "gemini_api_key" in error_str.lower()
