"""Configuration management module.

This module handles all configuration settings for the GitHub Stars MCP Server,
including GitHub personal access token authentication, Redis connection, and other service settings.
"""

from typing import Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings configuration.
    
    This class manages all configuration settings for the GitHub Stars MCP Server.
    Settings can be loaded from environment variables or .env file.
    
    Attributes:
        github_token: GitHub personal access token for API authentication
        redis_url: Optional Redis connection URL for caching
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    github_token: str
    redis_url: Optional[str] = "redis://localhost:6379/0"
    log_level: str = "INFO"
    dangerously_omit_auth: bool = True
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        if normalized not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return normalized
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()