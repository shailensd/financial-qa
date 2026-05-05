"""
Unit tests for LLM Router.

Tests verify:
1. Model name mapping (llama, gemma, gemini)
2. Retry logic for timeout exceptions
3. Sequential execution (not concurrent)
4. Error handling for unknown models
5. API key configuration for Gemini
"""

import pytest
from unittest.mock import Mock, patch, call
from litellm.exceptions import Timeout, APIConnectionError

from app.ml.llm_router import LLMRouter


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def router():
    """Create an LLM router instance."""
    return LLMRouter(
        ollama_base_url="http://localhost:11434",
        gemini_api_key="test_gemini_key"
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"}
    ]


# ============================================================================
# Unit Tests
# ============================================================================

class TestModelMapping:
    """Tests for model name mapping."""
    
    def test_llama_model_mapping(self, router):
        """Test that 'llama' maps to correct Ollama model."""
        assert router.MODELS["llama"] == "ollama/llama3.2:3b"
    
    def test_gemma_model_mapping(self, router):
        """Test that 'gemma' maps to correct Ollama model."""
        assert router.MODELS["gemma"] == "ollama/gemma2:9b"
    
    def test_gemini_model_mapping(self, router):
        """Test that 'gemini' maps to correct Gemini model."""
        assert router.MODELS["gemini"] == "gemini/gemini-2.0-flash"
    
    def test_unknown_model_raises_error(self, router, sample_messages):
        """Test that unknown model name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            router.complete("unknown_model", sample_messages)
        
        assert "Unknown model" in str(exc_info.value)
        assert "unknown_model" in str(exc_info.value)


class TestComplete:
    """Tests for complete method."""
    
    @patch('app.ml.llm_router.completion')
    def test_complete_calls_litellm_with_correct_model(self, mock_completion, router, sample_messages):
        """Test that complete calls LiteLLM with the correct model string."""
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "The answer is 4."
        mock_completion.return_value = mock_response
        
        result = router.complete("llama", sample_messages)
        
        # Verify LiteLLM was called with correct model
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "ollama/llama3.2:3b"
        assert call_kwargs["messages"] == sample_messages
        assert result == "The answer is 4."
    
    @patch('app.ml.llm_router.completion')
    def test_complete_passes_additional_kwargs(self, mock_completion, router, sample_messages):
        """Test that complete passes additional kwargs to LiteLLM."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response
        
        router.complete(
            "gemma",
            sample_messages,
            temperature=0.7,
            max_tokens=100
        )
        
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 100
    
    @patch('app.ml.llm_router.completion')
    def test_complete_adds_api_key_for_gemini(self, mock_completion, router, sample_messages):
        """Test that complete adds API key for Gemini models."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response
        
        router.complete("gemini", sample_messages)
        
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["api_key"] == "test_gemini_key"
    
    @patch('app.ml.llm_router.completion')
    def test_complete_does_not_add_api_key_for_ollama(self, mock_completion, router, sample_messages):
        """Test that complete does not add API key for Ollama models."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response
        
        router.complete("llama", sample_messages)
        
        call_kwargs = mock_completion.call_args[1]
        assert "api_key" not in call_kwargs


class TestRetryLogic:
    """Tests for retry logic."""
    
    @patch('app.ml.llm_router.completion')
    def test_retry_once_on_timeout(self, mock_completion, router, sample_messages):
        """Test that retry_once retries once on Timeout exception."""
        # First call raises Timeout, second call succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Success after retry"
        
        mock_completion.side_effect = [
            Timeout("Request timed out", model="test_model", llm_provider="test_provider"),
            mock_response
        ]
        
        result = router.complete("llama", sample_messages)
        
        # Verify two calls were made
        assert mock_completion.call_count == 2
        assert result == "Success after retry"
    
    @patch('app.ml.llm_router.completion')
    def test_retry_once_on_api_connection_error(self, mock_completion, router, sample_messages):
        """Test that retry_once retries once on APIConnectionError."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Success after retry"
        
        mock_completion.side_effect = [
            APIConnectionError("Connection failed", llm_provider="test_provider", model="test_model"),
            mock_response
        ]
        
        result = router.complete("gemma", sample_messages)
        
        assert mock_completion.call_count == 2
        assert result == "Success after retry"
    
    @patch('app.ml.llm_router.completion')
    def test_raises_timeout_after_two_failures(self, mock_completion, router, sample_messages):
        """Test that Timeout is raised after both attempts fail."""
        # Both calls raise Timeout
        mock_completion.side_effect = [
            Timeout("Request timed out", model="test_model", llm_provider="test_provider"),
            Timeout("Request timed out again", model="test_model", llm_provider="test_provider")
        ]
        
        with pytest.raises(Timeout):
            router.complete("llama", sample_messages)
        
        # Verify two calls were made
        assert mock_completion.call_count == 2
    
    @patch('app.ml.llm_router.completion')
    def test_raises_api_connection_error_after_two_failures(self, mock_completion, router, sample_messages):
        """Test that APIConnectionError is raised after both attempts fail."""
        mock_completion.side_effect = [
            APIConnectionError("Connection failed", llm_provider="test_provider", model="test_model"),
            APIConnectionError("Connection failed again", llm_provider="test_provider", model="test_model")
        ]
        
        with pytest.raises(APIConnectionError):
            router.complete("gemini", sample_messages)
        
        assert mock_completion.call_count == 2
    
    @patch('app.ml.llm_router.completion')
    def test_no_retry_on_other_exceptions(self, mock_completion, router, sample_messages):
        """Test that other exceptions are not retried."""
        # Raise a different exception
        mock_completion.side_effect = ValueError("Invalid parameter")
        
        with pytest.raises(ValueError):
            router.complete("llama", sample_messages)
        
        # Verify only one call was made (no retry)
        assert mock_completion.call_count == 1
    
    @patch('app.ml.llm_router.completion')
    def test_no_retry_on_success(self, mock_completion, router, sample_messages):
        """Test that successful calls are not retried."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Success on first try"
        mock_completion.return_value = mock_response
        
        result = router.complete("llama", sample_messages)
        
        # Verify only one call was made
        assert mock_completion.call_count == 1
        assert result == "Success on first try"


class TestSequentialExecution:
    """Tests for sequential execution guarantee."""
    
    @patch('app.ml.llm_router.completion')
    def test_multiple_calls_are_sequential(self, mock_completion, router, sample_messages):
        """
        Test that multiple model calls are executed sequentially.
        
        This test verifies that the router does not use concurrent execution
        (e.g., asyncio, threading) which would cause RAM pressure.
        """
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response
        
        # Make multiple calls
        router.complete("llama", sample_messages)
        router.complete("gemma", sample_messages)
        router.complete("gemini", sample_messages)
        
        # Verify calls were made in order (not concurrent)
        assert mock_completion.call_count == 3
        
        # Verify each call completed before the next started
        # (if they were concurrent, we'd see different behavior in call order)
        calls = mock_completion.call_args_list
        assert calls[0][1]["model"] == "ollama/llama3.2:3b"
        assert calls[1][1]["model"] == "ollama/gemma2:9b"
        assert calls[2][1]["model"] == "gemini/gemini-2.0-flash"


class TestInitialization:
    """Tests for router initialization."""
    
    def test_initialization_with_defaults(self):
        """Test that router can be initialized with default values."""
        router = LLMRouter()
        
        assert router.ollama_base_url == "http://localhost:11434"
        assert router.gemini_api_key is None
    
    def test_initialization_with_custom_values(self):
        """Test that router can be initialized with custom values."""
        router = LLMRouter(
            ollama_base_url="http://custom:8080",
            gemini_api_key="custom_key"
        )
        
        assert router.ollama_base_url == "http://custom:8080"
        assert router.gemini_api_key == "custom_key"
    
    @patch('app.ml.llm_router.litellm')
    def test_initialization_configures_litellm(self, mock_litellm):
        """Test that initialization configures LiteLLM settings."""
        router = LLMRouter(ollama_base_url="http://test:1234")
        
        # Verify LiteLLM was configured
        assert mock_litellm.api_base == "http://test:1234"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @patch('app.ml.llm_router.completion')
    def test_empty_messages_list(self, mock_completion, router):
        """Test handling of empty messages list."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_completion.return_value = mock_response
        
        result = router.complete("llama", [])
        
        assert mock_completion.call_count == 1
        assert result == "Response"
    
    @patch('app.ml.llm_router.completion')
    def test_response_with_empty_content(self, mock_completion, router, sample_messages):
        """Test handling of response with empty content."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = ""
        mock_completion.return_value = mock_response
        
        result = router.complete("llama", sample_messages)
        
        assert result == ""
    
    def test_router_without_gemini_api_key(self, sample_messages):
        """Test that router works for Ollama models without Gemini API key."""
        router = LLMRouter(gemini_api_key=None)
        
        with patch('app.ml.llm_router.completion') as mock_completion:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Response"
            mock_completion.return_value = mock_response
            
            result = router.complete("llama", sample_messages)
            
            # Verify no api_key was passed
            call_kwargs = mock_completion.call_args[1]
            assert "api_key" not in call_kwargs
            assert result == "Response"
