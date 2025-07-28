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
    """Fetch comprehensive details for a single GitHub repository, including README content.
    
    **When to use this tool:**
    - When you need detailed information about a specific repository
    - To get the README content for understanding project purpose and usage
    - When a user asks specific questions about a single repository
    - For in-depth analysis of a particular project
    
    **Key features:**
    - Retrieves complete README.md content as plain text
    - Provides repository metadata and statistics
    - Optimized for single repository queries
    - Fast response time for individual repository analysis
    
    **Usage patterns:**
    - Use after getting repository lists to dive deeper into specific repos
    - Ideal for answering questions about project documentation
    - Combine with starred repository lists for targeted analysis
    - Perfect for README content analysis and project understanding

    Args:
        repo_id: Repository identifier in 'owner/repository' format (e.g., 'microsoft/vscode')

    Returns:
        RepositoryDetails containing:
        - readme_content: Full README.md content as plain text
        - description: Repository description
        - topics: List of repository topics/tags
        - languages: List of programming languages used

    Raises:
        ValidationError: If repo_id format is invalid (must be 'owner/repo' format)
        GitHubAPIError: If repository not found, access denied, or API request fails
    """
    return await _get_repo_details_impl(ctx, repo_id)
