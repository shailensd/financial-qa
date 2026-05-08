"""
Configuration management for FinDoc Intelligence.

This module provides centralized configuration using Pydantic BaseSettings,
loading values from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Required fields (must be set via environment variables):
    - database_url: PostgreSQL connection string
    - gemini_api_key: Google AI Studio API key for Gemini 2.0 Flash
    
    Optional fields have defaults suitable for development.
    """
    
    # Chunking configuration
    chunk_size: int = 800
    chunk_overlap: int = 200
    
    # Retrieval configuration
    retrieval_top_k: int = 10
    
    # Agent configuration
    max_repair_iterations: int = 2
    memory_summarization_interval: int = 5
    memory_summary_max_words: int = 150
    
    # Database configuration
    database_url: str  # Required - no default
    chroma_persist_dir: str = "./chroma_db"
    
    # LLM configuration
    ollama_base_url: str = "http://localhost:11434"
    gemini_api_key: str  # Required - no default
    groq_api_key: Optional[str] = None  # Optional - for Groq-hosted open-source models
    
    # Evaluation configuration
    few_shot_dedup_threshold: float = 0.85
    
    @field_validator('database_url', 'gemini_api_key')
    @classmethod
    def validate_required_fields(cls, v: str, info) -> str:
        """
        Validate that required fields are not empty.
        
        Raises:
            ValueError: If the field is None, empty string, or whitespace-only
        """
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(
                f"{info.field_name} is required and must be set via environment variable. "
                f"Please set {info.field_name.upper()} in your .env file or environment."
            )
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance - only instantiate when environment variables are properly set
# In production, this will be instantiated after environment is configured
# In tests, instantiate Settings() directly with proper environment setup
try:
    settings = Settings()
except Exception:
    # Allow module import even if settings are not configured
    # This is useful for testing and development
    settings = None  # type: ignore
