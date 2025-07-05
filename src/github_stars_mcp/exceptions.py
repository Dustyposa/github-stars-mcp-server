"""Custom exception classes for GitHub Stars MCP Server.

This module defines all custom exceptions used throughout the application,
including GitHub API related exceptions and MCP server specific errors.
"""

from typing import Optional, Any, Dict


class GitHubStarsMCPError(Exception):
    """Base exception class for GitHub Stars MCP Server.
    
    This is the root exception class for all custom exceptions in the application.
    All other custom exceptions should inherit from this class.
    
    Attributes:
        message: Human-readable error message
        error_code: Optional error code for programmatic handling
        details: Optional dictionary containing additional error details
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class GitHubAPIError(GitHubStarsMCPError):
    """Base exception class for GitHub API related errors.
    
    This exception is raised when there are issues communicating with the GitHub API,
    including network errors, API errors, and response parsing errors.
    
    Attributes:
        status_code: HTTP status code from the API response (if available)
        response_data: Raw response data from the API (if available)
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, error_code, details)
        self.status_code = status_code
        self.response_data = response_data or {}


class RateLimitError(GitHubAPIError):
    """Exception raised when GitHub API rate limit is exceeded.
    
    This exception is raised when the application hits GitHub's API rate limits.
    It includes information about when the rate limit will reset.
    
    Attributes:
        reset_time: Unix timestamp when the rate limit will reset
        remaining_requests: Number of requests remaining in the current window
    """
    
    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_time: Optional[int] = None,
        remaining_requests: Optional[int] = None,
        **kwargs
    ) -> None:
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)
        self.reset_time = reset_time
        self.remaining_requests = remaining_requests


class AuthenticationError(GitHubAPIError):
    """Exception raised when GitHub API authentication fails.
    
    This exception is raised when the provided GitHub token is invalid,
    expired, or lacks the necessary permissions.
    """
    
    def __init__(
        self,
        message: str = "GitHub API authentication failed",
        **kwargs
    ) -> None:
        super().__init__(message, error_code="AUTHENTICATION_FAILED", **kwargs)


class ValidationError(GitHubStarsMCPError):
    """Exception raised when data validation fails.
    
    This exception is raised when input data doesn't meet the expected format
    or constraints, such as invalid usernames, malformed requests, etc.
    
    Attributes:
        field_errors: Dictionary mapping field names to their validation errors
    """
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_errors = field_errors or {}


class ConfigurationError(GitHubStarsMCPError):
    """Exception raised when there are configuration issues.
    
    This exception is raised when required configuration is missing
    or invalid, such as missing environment variables or invalid settings.
    """
    
    def __init__(
        self,
        message: str = "Configuration error",
        **kwargs
    ) -> None:
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)


class CacheError(GitHubStarsMCPError):
    """Exception raised when cache operations fail.
    
    This exception is raised when there are issues with cache operations,
    such as Redis connection failures or cache corruption.
    """
    
    def __init__(
        self,
        message: str = "Cache operation failed",
        **kwargs
    ) -> None:
        super().__init__(message, error_code="CACHE_ERROR", **kwargs)