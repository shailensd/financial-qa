"""
Unit tests for structured logging.

Tests the StructuredLogger class to verify:
1. Log entry creation and sanitization
2. API key and credential filtering
3. Database persistence via CRUD operations
4. Error handling for logging failures
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.logging import StructuredLogger, SENSITIVE_PATTERNS


class TestStructuredLogger:
    """Test suite for StructuredLogger class."""
    
    def test_init(self):
        """Test StructuredLogger initialization."""
        logger = StructuredLogger()
        assert logger is not None
        assert logger._sensitive_regex is not None
    
    def test_sanitize_value_with_api_key(self):
        """Test that API keys are redacted from log values."""
        logger = StructuredLogger()
        
        # Test various API key field names
        assert logger._sanitize_value("api_key", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("API_KEY", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("gemini_api_key", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("apiKey", "secret123") == "[REDACTED]"
    
    def test_sanitize_value_with_password(self):
        """Test that passwords are redacted from log values."""
        logger = StructuredLogger()
        
        assert logger._sanitize_value("password", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("PASSWORD", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("db_password", "secret123") == "[REDACTED]"
    
    def test_sanitize_value_with_token(self):
        """Test that tokens are redacted from log values."""
        logger = StructuredLogger()
        
        assert logger._sanitize_value("token", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("auth_token", "secret123") == "[REDACTED]"
        assert logger._sanitize_value("bearer_token", "secret123") == "[REDACTED]"
    
    def test_sanitize_value_with_safe_fields(self):
        """Test that non-sensitive fields are not redacted."""
        logger = StructuredLogger()
        
        # Safe field names should pass through unchanged
        assert logger._sanitize_value("query_text", "What is revenue?") == "What is revenue?"
        assert logger._sanitize_value("model_used", "gemini") == "gemini"
        assert logger._sanitize_value("session_id", "abc123") == "abc123"
        assert logger._sanitize_value("repair_count", 2) == 2
    
    def test_sanitize_value_with_nested_dict(self):
        """Test that nested dictionaries are recursively sanitized."""
        logger = StructuredLogger()
        
        nested = {
            "query": "What is revenue?",
            "config": {
                "api_key": "secret123",
                "model": "gemini"
            }
        }
        
        sanitized = logger._sanitize_value("data", nested)
        
        assert sanitized["query"] == "What is revenue?"
        assert sanitized["config"]["api_key"] == "[REDACTED]"
        assert sanitized["config"]["model"] == "gemini"
    
    def test_sanitize_value_with_list(self):
        """Test that lists with dictionaries are recursively sanitized."""
        logger = StructuredLogger()
        
        list_data = [
            {"tool": "LOOKUP", "api_key": "secret123"},
            {"tool": "CALCULATE", "expression": "1+1"}
        ]
        
        sanitized = logger._sanitize_value("tool_results", list_data)
        
        assert sanitized[0]["tool"] == "LOOKUP"
        assert sanitized[0]["api_key"] == "[REDACTED]"
        assert sanitized[1]["tool"] == "CALCULATE"
        assert sanitized[1]["expression"] == "1+1"
    
    def test_sanitize_log_entry(self):
        """Test complete log entry sanitization."""
        logger = StructuredLogger()
        
        log_entry = {
            "session_id": "abc123",
            "query_text": "What is revenue?",
            "gemini_api_key": "secret123",
            "model_used": "gemini",
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple"}}
            ],
            "config": {
                "api_key": "another_secret",
                "base_url": "http://localhost"
            }
        }
        
        sanitized = logger._sanitize_log_entry(log_entry)
        
        # Safe fields preserved
        assert sanitized["session_id"] == "abc123"
        assert sanitized["query_text"] == "What is revenue?"
        assert sanitized["model_used"] == "gemini"
        assert sanitized["plan"][0]["tool"] == "LOOKUP"
        
        # Sensitive fields redacted
        assert sanitized["gemini_api_key"] == "[REDACTED]"
        assert sanitized["config"]["api_key"] == "[REDACTED]"
        
        # Nested safe fields preserved
        assert sanitized["config"]["base_url"] == "http://localhost"
    
    @pytest.mark.asyncio
    async def test_log_request_success(self):
        """Test successful log request persistence."""
        logger = StructuredLogger()
        
        # Mock database session
        mock_db = AsyncMock()
        
        # Mock crud.create_log
        with patch('app.logging.crud.create_log', new_callable=AsyncMock) as mock_create_log:
            mock_create_log.return_value = MagicMock(id=1)
            
            # Call log_request
            await logger.log_request(
                db=mock_db,
                session_id="test_session",
                query_id=42,
                query_text="What is Apple's revenue?",
                model_used="gemini",
                plan=[{"tool": "LOOKUP", "inputs": {"entity": "Apple"}}],
                tool_results=[{"tool": "LOOKUP", "status": "success", "output": {"chunk_text": "Revenue: $383B"}}],
                chunk_ids=[1, 2, 3],
                refusal_decision=False,
                critic_verdict="approved",
                repair_count=0,
                total_latency_ms=1500,
                confidence_score=0.92,
            )
            
            # Verify crud.create_log was called
            mock_create_log.assert_called_once()
            
            # Verify call arguments
            call_args = mock_create_log.call_args
            assert call_args.kwargs["session_id"] == "test_session"
            assert call_args.kwargs["query_id"] == 42
            
            # Verify log_json structure
            log_json = call_args.kwargs["log_json"]
            assert log_json["query_text"] == "What is Apple's revenue?"
            assert log_json["model_used"] == "gemini"
            assert log_json["refusal_decision"] is False
            assert log_json["critic_verdict"] == "approved"
            assert log_json["repair_count"] == 0
            assert log_json["total_latency_ms"] == 1500
            assert log_json["confidence_score"] == 0.92
            assert len(log_json["chunk_ids"]) == 3
    
    @pytest.mark.asyncio
    async def test_log_request_with_refusal(self):
        """Test log request with refusal decision."""
        logger = StructuredLogger()
        
        mock_db = AsyncMock()
        
        with patch('app.logging.crud.create_log', new_callable=AsyncMock) as mock_create_log:
            mock_create_log.return_value = MagicMock(id=1)
            
            await logger.log_request(
                db=mock_db,
                session_id="test_session",
                query_id=42,
                query_text="Should I buy Apple stock?",
                model_used="gemini",
                plan=[],
                tool_results=[],
                chunk_ids=[],
                refusal_decision=True,
                critic_verdict="n/a",
                repair_count=0,
                total_latency_ms=100,
                refusal_reason="investment_advice_prohibited",
            )
            
            # Verify refusal was logged
            call_args = mock_create_log.call_args
            log_json = call_args.kwargs["log_json"]
            assert log_json["refusal_decision"] is True
            assert log_json["refusal_reason"] == "investment_advice_prohibited"
    
    @pytest.mark.asyncio
    async def test_log_request_with_api_key_sanitization(self):
        """Test that API keys in tool results are sanitized."""
        logger = StructuredLogger()
        
        mock_db = AsyncMock()
        
        with patch('app.logging.crud.create_log', new_callable=AsyncMock) as mock_create_log:
            mock_create_log.return_value = MagicMock(id=1)
            
            # Tool results containing API key
            tool_results = [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "config": {
                        "api_key": "secret123",
                        "model": "gemini"
                    }
                }
            ]
            
            await logger.log_request(
                db=mock_db,
                session_id="test_session",
                query_id=42,
                query_text="What is revenue?",
                model_used="gemini",
                plan=[],
                tool_results=tool_results,
                chunk_ids=[],
                refusal_decision=False,
                critic_verdict="approved",
                repair_count=0,
                total_latency_ms=1000,
            )
            
            # Verify API key was redacted
            call_args = mock_create_log.call_args
            log_json = call_args.kwargs["log_json"]
            assert log_json["tool_results"][0]["config"]["api_key"] == "[REDACTED]"
            assert log_json["tool_results"][0]["config"]["model"] == "gemini"
    
    @pytest.mark.asyncio
    async def test_log_request_database_error(self):
        """Test that database errors are caught and logged."""
        logger = StructuredLogger()
        
        mock_db = AsyncMock()
        
        # Mock crud.create_log to raise an exception
        with patch('app.logging.crud.create_log', new_callable=AsyncMock) as mock_create_log:
            mock_create_log.side_effect = Exception("Database connection failed")
            
            # Should not raise exception - errors are logged but not propagated
            await logger.log_request(
                db=mock_db,
                session_id="test_session",
                query_id=42,
                query_text="What is revenue?",
                model_used="gemini",
                plan=[],
                tool_results=[],
                chunk_ids=[],
                refusal_decision=False,
                critic_verdict="approved",
                repair_count=0,
                total_latency_ms=1000,
            )
            
            # Verify create_log was called (and failed)
            mock_create_log.assert_called_once()
    
    def test_format_log_for_display(self):
        """Test log formatting for human-readable display."""
        logger = StructuredLogger()
        
        log_json = {
            "session_id": "test_session",
            "query_text": "What is Apple's revenue?",
            "model_used": "gemini",
            "timestamp": "2024-01-15T10:30:00",
            "refusal_decision": False,
            "critic_verdict": "approved",
            "repair_count": 1,
            "confidence_score": 0.92,
            "total_latency_ms": 1500,
            "plan": [
                {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue"}}
            ],
            "tool_results": [
                {"tool": "LOOKUP", "status": "success"}
            ],
            "chunk_ids": [1, 2, 3]
        }
        
        formatted = logger.format_log_for_display(log_json)
        
        # Verify key information is present
        assert "test_session" in formatted
        assert "What is Apple's revenue?" in formatted
        assert "gemini" in formatted
        assert "approved" in formatted
        assert "Repair Count: 1" in formatted
        assert "Confidence Score: 0.92" in formatted
        assert "Latency: 1500ms" in formatted
        assert "LOOKUP" in formatted
        assert "Citations: 3 chunks" in formatted
    
    def test_format_log_for_display_with_refusal(self):
        """Test log formatting with refusal reason."""
        logger = StructuredLogger()
        
        log_json = {
            "session_id": "test_session",
            "query_text": "Should I buy Apple stock?",
            "model_used": "gemini",
            "timestamp": "2024-01-15T10:30:00",
            "refusal_decision": True,
            "refusal_reason": "investment_advice_prohibited",
            "critic_verdict": "n/a",
            "repair_count": 0,
            "confidence_score": None,
            "total_latency_ms": 100,
            "plan": [],
            "tool_results": [],
            "chunk_ids": []
        }
        
        formatted = logger.format_log_for_display(log_json)
        
        # Verify refusal information is present
        assert "Refusal: True" in formatted
        assert "investment_advice_prohibited" in formatted
