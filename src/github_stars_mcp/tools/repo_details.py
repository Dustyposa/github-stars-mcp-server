"""Single repository details MCP tool."""

import asyncio

import structlog
from fastmcp import Context

from ..common.error_handlers import handle_github_api_errors
from ..common.github_helpers import ensure_github_client
from ..common.logging_helpers import log_function_call
from ..exceptions import GitHubAPIError
from ..models import RepositoryDetails
from ..shared import mcp
from .batch_repo_details import fetch_single_repository_details

# Get structured logger
logger = structlog.get_logger(__name__)


@handle_github_api_errors("get repository details")
@log_function_call("get_repo_details_impl")
async def _get_repo_details_impl(ctx: Context, repo_id: str) -> RepositoryDetails:
    """Internal implementation for getting repository details.

    This function contains the core logic that can be called from other tools.

    Args:
        ctx: FastMCP context
        repo_id: Repository ID to fetch details for

    Returns:
        RepositoryDetails containing repository information and README content

    Raises:
        ValidationError: If repo_id format is invalid
        GitHubAPIError: If GitHub API request fails
    """
    await ctx.info(f"Fetching details for repository: {repo_id}")

    # Create semaphore for consistency with batch function
    semaphore = asyncio.Semaphore(1)

    # Ensure GitHub client is available
    from .. import shared
    github_client = ensure_github_client(shared.github_client)

    # Use the existing fetch function from batch_repo_details
    result = await fetch_single_repository_details(
        ctx, repo_id, github_client, semaphore
    )

    if result is None:
        raise GitHubAPIError(f"Failed to fetch details for repository: {repo_id}")

    await ctx.info(f"Successfully fetched details for {repo_id}")
    return result


@mcp.tool
@log_function_call("get_repo_details")
async def get_repo_details(ctx: Context, repo_id: str) -> RepositoryDetails:
    """
    为一个指定的 GitHub 仓库检索其详细信息，包括 README.md 文件的纯文本内容。当需要深入了解某一个特定项目时，或者当用户明确询问关于单个项目的信息时，使用此工具。

    Args:
        ctx: FastMCP context
        repo_id: Repository ID to fetch details for

    Returns:
        RepositoryDetails containing repository information and README content

    Raises:
        ValidationError: If repo_id format is invalid
        GitHubAPIError: If GitHub API request fails
    """
    return await _get_repo_details_impl(ctx, repo_id)
