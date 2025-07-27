"""Batch repository details MCP tool."""

import asyncio

import structlog
from fastmcp import Context

from ..exceptions import GitHubAPIError
from ..models import BatchRepositoryDetailsResponse, RepositoryDetails
from ..shared import mcp

# Get structured logger
logger = structlog.get_logger(__name__)


def validate_repository_names(repository_names: list[str]) -> list[str]:
    """Validate repository names format (owner/repo)."""
    if not repository_names:
        raise ValueError("Repository names list cannot be empty")

    if len(repository_names) > 50:
        raise ValueError("Cannot process more than 50 repositories at once")

    validated_names = []
    for repo_name in repository_names:
        if not repo_name or not repo_name.strip():
            raise ValueError("Repository name cannot be empty")

        repo_name = repo_name.strip()
        if "/" not in repo_name:
            raise ValueError(
                f"Invalid repository name format: {repo_name}. Expected format: owner/repo"
            )

        parts = repo_name.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid repository name format: {repo_name}. Expected format: owner/repo"
            )

        validated_names.append(repo_name)

    return validated_names


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


async def _get_batch_repo_details_impl(
    ctx: Context,
    repo_ids: list[str],
) -> BatchRepositoryDetailsResponse:
    """Internal implementation for getting batch repository details.

    This function contains the core logic that can be called from other tools.
    """
    from .. import shared

    if not shared.github_client:
        await ctx.error("GitHub client not initialized")
        raise GitHubAPIError("GitHub client not initialized")

    result = await fetch_multi_repository_details(ctx, repo_ids, shared.github_client)
    try:
        return result
    except Exception as e:
        await ctx.error(f"Batch repository details fetch failed: {str(e)}")
        raise GitHubAPIError(f"Batch repository details fetch failed: {str(e)}") from e


@mcp.tool
async def get_batch_repo_details(
    ctx: Context,
    repo_ids: list[str],
) -> BatchRepositoryDetailsResponse:
    """
    接收一个仓库标识符的列表，并一次性批量返回所有这些仓库的详细信息，包括它们的 README 内容。当你需要比较少数几个特定项目，或者在获取到一个仓库列表后需要进一步获取它们的详细内容时，使用此工具以提高效率。
    """
    return await _get_batch_repo_details_impl(ctx, repo_ids)
