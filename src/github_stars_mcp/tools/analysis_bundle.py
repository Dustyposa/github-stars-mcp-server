"""High-level analysis bundle tool for GitHub starred repositories."""
import asyncio
from asyncio import gather, Semaphore
from collections import Counter
from typing import Any

import structlog
from fastmcp import Context

from ..cache.decorators import multi_level_cache
from ..exceptions import GitHubAPIError
from ..models import (
    AnalysisBundle,
    StarredRepositoriesResponse,
    StarredRepositoriesWithReadmeResponse,
    StartedRepoWithReadme,
)
from ..shared import mcp
from .batch_repo_details import _get_batch_repo_details_impl
from .starred_repo_list import _get_user_starred_repositories_impl

logger = structlog.get_logger(__name__)


# 使用 itertools 方法分组
from itertools import islice

def chunk_list(iterable, chunk_size):
    iterator = iter(iterable)
    while chunk := list(islice(iterator, chunk_size)):
        yield chunk


@mcp.tool
# @multi_level_cache(ttl=1800, file_ttl=7200)  # 30 min L1, 2 hours L2
async def create_full_analysis_bundle(
    ctx: Context,
    username: str | None = None,
    include_readme: bool = True,
    max_repositories: int = 100,
    concurrent_requests: int = 10
) -> StarredRepositoriesWithReadmeResponse:
    """Create comprehensive analysis bundle for user starred repositories.

    This high-level tool combines multiple operations to generate a complete
    analysis of a user's starred repositories, including detailed information
    and statistical analysis.

    Args:
        username: GitHub username to analyze (optional, uses authenticated user if not provided)
        include_readme: Whether to include README content in repository details
        max_repositories: Maximum number of repositories to analyze (1-200, default: 100)
        concurrent_requests: Number of concurrent requests for batch operations (1-20, default: 10)

    Returns:
        StarredRepositoriesWithReadmeResponse containing complete repository analysis

    Raises:
        GitHubAPIError: If GitHub API requests fail
        ValueError: If parameters are invalid
    """
    # Validate parameters
    if max_repositories < 1 or max_repositories > 200:
        raise ValueError("max_repositories must be between 1 and 200")

    if concurrent_requests < 1 or concurrent_requests > 20:
        raise ValueError("concurrent_requests must be between 1 and 20")

    logger.info(
        "Starting starred repository analysis bundle creation",
        username=username or "authenticated_user",
        max_repositories=max_repositories,
        include_readme=include_readme
    )
    stated_repo_map = {}

    try:
        # Step 1: Get starred repositories list
        await ctx.info("Fetching starred repositories list")
        starred_data = await _get_user_starred_repositories_impl(
            ctx=ctx,
            username=username,
        )
        for repo in starred_data.repositories:
            stated_repo_map[repo.repo_id] = StartedRepoWithReadme.model_construct(
                **repo.model_dump()
            )

        while starred_data.has_next_page:
            if len(stated_repo_map.keys()) >= max_repositories:
                break
            await ctx.info(f"Fetching next page of starred repositories, lens: {len(stated_repo_map.keys())}")
            starred_data = await _get_user_starred_repositories_impl(
                ctx=ctx,
                username=username,
                cursor=starred_data.end_cursor
            )
            for repo in starred_data.repositories:
                stated_repo_map[repo.repo_id] = StartedRepoWithReadme.model_construct(
                    **repo.model_dump()
                )



        await ctx.info(
            f"Fetching detailed repository information, {len(stated_repo_map.keys())}",
        )
        # 100 个分组
        chunked_repo_ids = list(chunk_list(list(stated_repo_map.keys()), 100))
        # 控制并发数量
        semaphore = Semaphore(concurrent_requests)

        async def fetch_chunk_details(ctx, repo_ids_chunk):
            async with semaphore:
                return await _get_batch_repo_details_impl(
                    ctx=ctx, repo_ids=repo_ids_chunk,
                )

        # 创建并发任务
        tasks = [
            fetch_chunk_details(ctx, chunk)
            for chunk in chunked_repo_ids
        ]
        chunk_results = await asyncio.gather(*tasks)
        i = 1
        for result in chunk_results:
            for id_, readme_schema in result.data.items():
                i += 1
                if i <= 10:
                    logger.debug(f"{id_=}, {readme_schema=}")
                stated_repo_map[id_].readme_content = readme_schema.readme_content

        return StarredRepositoriesWithReadmeResponse(
            total_count=len(stated_repo_map.keys()),
            repositories=list(stated_repo_map.values()),
        )

    except GitHubAPIError:
        raise
    except Exception as e:
        await ctx.error(
            f"Failed to create analysis bundle, {username}, error: {str(e)}",
        )
        raise GitHubAPIError(f"Failed to create analysis bundle: {str(e)}")


