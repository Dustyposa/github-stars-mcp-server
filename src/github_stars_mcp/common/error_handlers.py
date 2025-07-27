"""Common error handling utilities."""

from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import structlog

from ..exceptions import GitHubAPIError, ValidationError

logger = structlog.get_logger(__name__)

T = TypeVar('T')


def handle_github_api_errors(operation_name: str):
    """Decorator to handle GitHub API errors consistently.

    Args:
        operation_name: Name of the operation for logging
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except ValidationError:
                # Re-raise validation errors as-is
                raise
            except GitHubAPIError:
                # Re-raise GitHub API errors as-is
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in {operation_name}",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise GitHubAPIError(
                    f"Failed to {operation_name}: {str(e)}"
                ) from e
        return wrapper
    return decorator








def create_github_api_error(message: str, original_error: Exception) -> GitHubAPIError:
    """Create a GitHubAPIError with proper error chaining.

    Args:
        message: Error message
        original_error: The original exception that caused this error

    Returns:
        GitHubAPIError with proper error chaining
    """
    logger.error(
        message,
        original_error=str(original_error),
        original_error_type=type(original_error).__name__
    )
    error = GitHubAPIError(message)
    raise error from original_error
