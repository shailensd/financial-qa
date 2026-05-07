"""
LLM Router for FinDoc Intelligence.

This module provides a unified interface for calling multiple LLM models
through LiteLLM, with retry logic and sequential execution to avoid RAM pressure.
"""

from typing import List, Dict, Any, Optional
import litellm
from litellm import completion
from litellm.exceptions import Timeout, APIConnectionError


class LLMRouter:
    """
    Router for LLM model calls using LiteLLM.
    
    Provides a unified interface for calling:
    - Llama 3.2 3B via Ollama
    - Gemma 2 9B via Ollama
    - Gemini 2.0 Flash via Google AI Studio
    
    Models are called sequentially (never concurrently) to avoid RAM pressure.
    Implements retry logic for timeout exceptions.
    """
    
    # Model name mappings
    MODELS = {
        "llama": "ollama/llama3.2:3b",
        "gemma": "ollama/gemma2:9b",
        "gemini": "gemini/gemini-2.5-flash"
    }
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434", gemini_api_key: Optional[str] = None):
        """
        Initialize the LLM router.
        
        Args:
            ollama_base_url: Base URL for Ollama API (default: http://localhost:11434)
            gemini_api_key: API key for Google AI Studio (required for Gemini)
        """
        self.ollama_base_url = ollama_base_url
        self.gemini_api_key = gemini_api_key
        
        # Configure LiteLLM
        litellm.set_verbose = False
        
        # Set API base for Ollama models
        if ollama_base_url:
            litellm.api_base = ollama_base_url
    
    def complete(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Call an LLM model with the given messages.
        
        Args:
            model: Model name ("llama", "gemma", or "gemini")
            messages: List of message dicts with "role" and "content" keys
            **kwargs: Additional arguments to pass to LiteLLM (temperature, max_tokens, etc.)
        
        Returns:
            The model's response text
        
        Raises:
            ValueError: If model name is not recognized
            Timeout: If the API call times out after retry
            APIConnectionError: If connection to the API fails after retry
        """
        # Map model name to LiteLLM model string
        if model not in self.MODELS:
            raise ValueError(
                f"Unknown model: {model}. Must be one of: {list(self.MODELS.keys())}"
            )
        
        litellm_model = self.MODELS[model]
        
        # Call with retry logic
        return self._retry_once(litellm_model, messages, **kwargs)
    
    def _retry_once(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Call LiteLLM with retry logic for timeout exceptions.
        
        Attempts the call once, and if it times out, retries once more before raising.
        
        Args:
            model: LiteLLM model string (e.g., "ollama/llama3.2:3b")
            messages: List of message dicts
            **kwargs: Additional arguments for LiteLLM
        
        Returns:
            The model's response text
        
        Raises:
            Timeout: If both attempts time out
            APIConnectionError: If connection fails on both attempts
        """
        # Prepare kwargs for LiteLLM
        call_kwargs = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        # Add API key for Gemini models
        if "gemini" in model and self.gemini_api_key:
            call_kwargs["api_key"] = self.gemini_api_key
        
        # First attempt
        try:
            response = completion(**call_kwargs)
            return response.choices[0].message.content
        except (Timeout, APIConnectionError) as e:
            # Retry once on timeout or connection error
            try:
                response = completion(**call_kwargs)
                return response.choices[0].message.content
            except (Timeout, APIConnectionError):
                # Re-raise the original exception after retry fails
                raise e
