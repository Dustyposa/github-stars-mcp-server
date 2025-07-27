"""Common GitHub client utilities."""


import structlog

from ..exceptions import GitHubAPIError
from ..utils.github_client import GitHubClient
from .error_handlers import create_github_api_error

logger = structlog.get_logger(__name__)


def ensure_github_client(github_client: GitHubClient | None) -> GitHubClient:
    """Ensure a GitHub client is available and properly configured.

    Args:
        github_client: Optional GitHub client instance

    Returns:
        Validated GitHub client

    Raises:
        GitHubAPIError: If client is not available or not configured
    """
    if github_client is None:
        raise GitHubAPIError("GitHub client not initialized")

    if not hasattr(github_client, 'token') or not github_client.token:
        raise GitHubAPIError("GitHub client not properly configured with token")

    return github_client


async def safe_github_request(operation: str, request_func, *args, **kwargs):
    """Safely execute a GitHub API request with consistent error handling.

    Args:
        operation: Description of the operation for logging
        request_func: The GitHub client method to call
        *args: Arguments to pass to the request function
        **kwargs: Keyword arguments to pass to the request function

    Returns:
        Result of the GitHub API request

    Raises:
        GitHubAPIError: If the request fails
    """
    try:
        logger.debug(f"Executing GitHub API request: {operation}")
        result = await request_func(*args, **kwargs)
        logger.debug(f"GitHub API request successful: {operation}")
        return result
    except Exception as e:
        error = create_github_api_error(
            f"GitHub API request failed for {operation}: {str(e)}",
            e
        )
        raise error from e
