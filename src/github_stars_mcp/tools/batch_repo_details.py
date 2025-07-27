"""Batch repository details MCP tool."""

import asyncio

import structlog
from fastmcp import Context

from ..common.error_handlers import handle_github_api_errors
from ..common.github_helpers import ensure_github_client
from ..common.logging_helpers import log_function_call
from ..common.validators import validate_repo_name
from ..exceptions import ValidationError
from ..models import BatchRepositoryDetailsResponse, RepositoryDetails
from ..shared import mcp

# Get structured logger
logger = structlog.get_logger(__name__)

# Configuration constants
MAX_BATCH_SIZE = 100


def validate_repository_ids(repo_ids: list[str]) -> list[str]:
    """Validate repository IDs list.

    Args:
        repo_ids: List of repository IDs to validate

    Returns:
        List of validated repository IDs

    Raises:
        ValidationError: If validation fails
    """
    if not repo_ids:
        raise ValidationError("Repository IDs list cannot be empty")

    if len(repo_ids) > MAX_BATCH_SIZE:
        raise ValidationError(f"Cannot process more than {MAX_BATCH_SIZE} repositories at once")

    validated_ids = []
    for repo_id in repo_ids:
        if not repo_id or not str(repo_id).strip():
            raise ValidationError("Repository ID cannot be empty")

        repo_id = str(repo_id).strip()

        # If it looks like owner/repo format, validate it
        if "/" in repo_id:
            validate_repo_name(repo_id)

        validated_ids.append(repo_id)

    return validated_ids


async def fetch_single_repository_details(
    ctx: Context, repo_id: str, github_client, semaphore: asyncio.Semaphore
) -> RepositoryDetails | None:
    """Fetch details for a single repository with concurrency control."""
    async with semaphore:
        try:
            await ctx.info(f"Fetching details for repository: {repo_id}")

            try:
                readme_result = await github_client.get_repository_readme(repo_id)

            except Exception as e:
                await ctx.info(f"Failed to fetch README for {repo_id}: {str(e)}")
            logger.debug(f"Readme content for {repo_id}: {readme_result}")
            # Create Repository and RepositoryDetails objects
            repo_details = RepositoryDetails(
                readme_content=readme_result["content"],
            )

            return repo_details

        except Exception as e:
            await ctx.error(f"Failed to fetch details for {repo_id}: {str(e)}")
            return None


async def fetch_multi_repository_details(
    ctx: Context,
    repo_ids: list[str],
    github_client,
) -> BatchRepositoryDetailsResponse:
    """Fetch details for multi repository with concurrency control."""
    readme_results = {}
    try:
        readme_results = await github_client.get_multi_repository_readme(repo_ids)

    except Exception as e:
        await ctx.info(f"Failed to fetch README for {repo_ids}: {str(e)}")

    return BatchRepositoryDetailsResponse(data=readme_results)


@handle_github_api_errors("get batch repository details")
@log_function_call("get_batch_repo_details_impl")
async def _get_batch_repo_details_impl(
    ctx: Context,
    repo_ids: list[str],
) -> BatchRepositoryDetailsResponse:
    """Internal implementation for getting batch repository details.

    This function contains the core logic that can be called from other tools.

    Args:
        ctx: FastMCP context
        repo_ids: List of repository IDs to fetch details for

    Returns:
        BatchRepositoryDetailsResponse containing repository details

    Raises:
        ValidationError: If repo_ids validation fails
        GitHubAPIError: If GitHub API request fails
    """
    # Validate repository IDs
    validated_repo_ids = validate_repository_ids(repo_ids)

    # Ensure GitHub client is available
    from .. import shared
    github_client = ensure_github_client(shared.github_client)

    # Fetch repository details
    result = await fetch_multi_repository_details(ctx, validated_repo_ids, github_client)
    return result


@mcp.tool
@log_function_call("get_batch_repo_details")
async def get_batch_repo_details(
    ctx: Context,
    repo_ids: list[str],
) -> BatchRepositoryDetailsResponse:
    """
    接收一个仓库标识符的列表，并一次性批量返回所有这些仓库的详细信息，包括它们的 README 内容。当你需要比较少数几个特定项目，或者在获取到一个仓库列表后需要进一步获取它们的详细内容时，使用此工具以提高效率。

    Args:
        ctx: FastMCP context
        repo_ids: List of repository IDs to fetch details for

    Returns:
        BatchRepositoryDetailsResponse containing repository details

    Raises:
        ValidationError: If repo_ids validation fails
        GitHubAPIError: If GitHub API request fails
    """
    return await _get_batch_repo_details_impl(ctx, repo_ids)
