"""High-level analysis bundle tool for GitHub starred repositories."""

import asyncio
from asyncio import Semaphore
from itertools import islice

import structlog
from fastmcp import Context

from ..common.error_handlers import handle_github_api_errors
from ..common.logging_helpers import log_function_call
from ..models import (
    StarredRepositoriesWithReadmeResponse,
    StartedRepoWithReadme,
)
from ..shared import mcp
from .batch_repo_details import _get_batch_repo_details_impl
from .starred_repo_list import _get_user_starred_repositories_impl

logger = structlog.get_logger(__name__)

# Configuration constants
MAX_REPOSITORIES_LIMIT = 200
MAX_CONCURRENT_REQUESTS = 20
DEFAULT_CHUNK_SIZE = 100


def chunk_list(iterable, chunk_size):
    """Split an iterable into chunks of specified size."""
    iterator = iter(iterable)
    while chunk := list(islice(iterator, chunk_size)):
        yield chunk


async def _fetch_all_starred_repositories(ctx: Context, username: str | None, max_repositories: int) -> dict:
    """Fetch all starred repositories up to the maximum limit.

    Args:
        ctx: FastMCP context
        username: GitHub username (optional)
        max_repositories: Maximum number of repositories to fetch

    Returns:
        Dictionary mapping repo_id to StartedRepoWithReadme objects
    """
    stated_repo_map = {}

    # Fetch initial page
    await ctx.info("Fetching starred repositories list")
    starred_data = await _get_user_starred_repositories_impl(ctx=ctx, username=username)

    for repo in starred_data.repositories:
        stated_repo_map[repo.repo_id] = StartedRepoWithReadme.model_construct(**repo.model_dump())

    # Fetch additional pages if needed
    while starred_data.has_next_page and len(stated_repo_map) < max_repositories:
        await ctx.info(f"Fetching next page of starred repositories, current count: {len(stated_repo_map)}")
        starred_data = await _get_user_starred_repositories_impl(
            ctx=ctx, username=username, cursor=starred_data.end_cursor
        )

        for repo in starred_data.repositories:
            if len(stated_repo_map) >= max_repositories:
                break
            stated_repo_map[repo.repo_id] = StartedRepoWithReadme.model_construct(**repo.model_dump())

    return stated_repo_map


async def _fetch_repository_details(ctx: Context, repo_ids: list, concurrent_requests: int) -> dict:
    """Fetch detailed information for repositories in batches.

    Args:
        ctx: FastMCP context
        repo_ids: List of repository IDs
        concurrent_requests: Number of concurrent requests

    Returns:
        Dictionary mapping repo_id to repository details
    """
    await ctx.info(f"Fetching detailed repository information for {len(repo_ids)} repositories")

    # Split into chunks
    chunked_repo_ids = list(chunk_list(repo_ids, DEFAULT_CHUNK_SIZE))
    semaphore = Semaphore(concurrent_requests)

    async def fetch_chunk_details(repo_ids_chunk):
        async with semaphore:
            return await _get_batch_repo_details_impl(ctx=ctx, repo_ids=repo_ids_chunk)

    # Execute concurrent requests
    tasks = [fetch_chunk_details(chunk) for chunk in chunked_repo_ids]
    chunk_results = await asyncio.gather(*tasks)

    # Combine results
    all_details = {}
    for result in chunk_results:
        all_details.update(result.data)

    return all_details


@handle_github_api_errors("create analysis bundle")
@log_function_call("create_full_analysis_bundle_impl")
async def _create_full_analysis_bundle_impl(
    ctx: Context,
    username: str | None = None,
) -> StarredRepositoriesWithReadmeResponse:
    """Internal implementation for creating comprehensive analysis bundle.

    This function contains the core logic that can be called from other tools.

    Args:
        ctx: FastMCP context
        username: GitHub username to analyze (optional, uses authenticated user if not provided)

    Returns:
        StarredRepositoriesWithReadmeResponse containing complete repository analysis

    Raises:
        GitHubAPIError: If GitHub API requests fail
    """
    # Use fixed default values
    max_repositories = 100
    concurrent_requests = 10

    logger.info(
        "Starting starred repository analysis bundle creation",
        username=username or "authenticated_user",
        max_repositories=max_repositories,
    )

    # Step 1: Fetch all starred repositories
    stated_repo_map = await _fetch_all_starred_repositories(ctx, username, max_repositories)

    # Step 2: Fetch detailed repository information if README is requested
    if stated_repo_map:
        repo_details = await _fetch_repository_details(
            ctx, list(stated_repo_map.keys()), concurrent_requests
        )

        # Update repositories with README content
        for repo_id, details in repo_details.items():
            if repo_id in stated_repo_map:
                stated_repo_map[repo_id].readme_content = details.readme_content

    return StarredRepositoriesWithReadmeResponse(
        total_count=len(stated_repo_map),
        repositories=list(stated_repo_map.values()),
    )


@mcp.tool
@log_function_call("create_full_analysis_bundle")
async def create_full_analysis_bundle(
    ctx: Context,
    username: str | None = None,
) -> StarredRepositoriesWithReadmeResponse:
    """Create comprehensive analysis bundle for user starred repositories.

    This high-level tool combines multiple operations to generate a complete
    analysis of a user's starred repositories, including detailed information
    and statistical analysis.

    Args:
        username: GitHub username to analyze (optional, uses authenticated user if not provided)

    Returns:
        StarredRepositoriesWithReadmeResponse containing complete repository analysis

    Raises:
        GitHubAPIError: If GitHub API requests fail
    """
    return await _create_full_analysis_bundle_impl(ctx, username)
