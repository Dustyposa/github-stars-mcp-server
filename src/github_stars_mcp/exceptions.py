"""Custom exception classes for GitHub Stars MCP Server."""

from typing import Any


class GitHubStarsMCPError(Exception):
    """Base exception class for GitHub Stars MCP Server."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
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
    """Base exception class for GitHub API related errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, details)
        self.status_code = status_code
        self.response_data = response_data or {}


class RateLimitError(GitHubAPIError):
    """Exception raised when GitHub API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_time: int | None = None,
        remaining_requests: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)
        self.reset_time = reset_time
        self.remaining_requests = remaining_requests


class AuthenticationError(GitHubAPIError):
    """Exception raised when GitHub API authentication fails."""

    def __init__(
        self, message: str = "GitHub API authentication failed", **kwargs
    ) -> None:
        super().__init__(message, error_code="AUTHENTICATION_FAILED", **kwargs)


class ValidationError(GitHubStarsMCPError):
    """Exception raised when data validation fails."""

    def __init__(
        self, message: str, field_errors: dict[str, str] | None = None, **kwargs
    ) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_errors = field_errors or {}


class ConfigurationError(GitHubStarsMCPError):
    """Exception raised when there are configuration issues."""

    def __init__(self, message: str = "Configuration error", **kwargs) -> None:
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)


class CacheError(GitHubStarsMCPError):
    """Exception raised when cache operations fail."""

    def __init__(self, message: str = "Cache operation failed", **kwargs) -> None:
        super().__init__(message, error_code="CACHE_ERROR", **kwargs)
