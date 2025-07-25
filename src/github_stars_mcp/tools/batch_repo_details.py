"""Batch repository details MCP tool."""

import asyncio
from datetime import datetime

import structlog
from fastmcp import Context

from ..exceptions import GitHubAPIError, ValidationError
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
            raise ValueError(f"Invalid repository name format: {repo_name}. Expected format: owner/repo")

        parts = repo_name.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repository name format: {repo_name}. Expected format: owner/repo")

        validated_names.append(repo_name)

    return validated_names


async def fetch_single_repository_details(
    ctx: Context,
    repo_name: str,
    github_client,
    semaphore: asyncio.Semaphore
) -> RepositoryDetails | None:
    """Fetch details for a single repository with concurrency control."""
    async with semaphore:
        try:
            await ctx.info(f"Fetching details for repository: {repo_name}")

            # Parse owner and name
            owner, name = repo_name.split("/", 1)

            # Create basic repository object
            repo_data = {
                "nameWithOwner": repo_name,
                "name": name,
                "owner": owner,
                "description": None,
                "stargazerCount": 0,
                "url": f"https://github.com/{repo_name}",
                "primaryLanguage": None,
                "starredAt": None,
                "pushedAt": None,
                "diskUsage": None,
                "repositoryTopics": [],
                "languages": []
            }

            # Get README content
            readme_data = None
            readme_size = None
            has_readme = False
            fetch_error = None
            
            try:
                readme_result = await github_client.get_repository_readme(owner, name)
                readme_data = readme_result.get("content")
                readme_size = readme_result.get("size")
                has_readme = readme_result.get("has_readme", False)
                fetch_error = readme_result.get("error")
                
                if has_readme:
                    await ctx.info(f"Successfully fetched README for {repo_name}")
                else:
                    await ctx.info(f"No README found for {repo_name}")
            except Exception as e:
                await ctx.info(f"Failed to fetch README for {repo_name}: {str(e)}")
                fetch_error = str(e)

            # Create Repository and RepositoryDetails objects
            repository = Repository.model_validate(repo_data)
            repo_details = RepositoryDetails(
                repository=repository,
                readme_content=readme_data,
                readme_size=readme_size,
                has_readme=has_readme,
                fetch_error=fetch_error
            )

            return repo_details

        except Exception as e:
            await ctx.error(f"Failed to fetch details for {repo_name}: {str(e)}")
            return None


@mcp.tool
async def get_batch_repo_details(
    ctx: Context,
    repository_names: list[str],
    max_concurrent: int = 10
) -> BatchRepositoryDetailsResponse:
    """Batch fetch repository details including README content.

    Args:
        repository_names: List of repository names in format 'owner/repo'
        max_concurrent: Maximum number of concurrent requests (default: 10, max: 20)

    Returns:
        BatchRepositoryDetailsResponse with repository details and processing statistics
    """

    # Validate parameters
    try:
        validated_names = validate_repository_names(repository_names)
    except ValueError as e:
        await ctx.error(f"Parameter validation failed: {str(e)}")
        raise ValidationError(str(e))

    if max_concurrent < 1 or max_concurrent > 20:
        await ctx.error(f"max_concurrent must be between 1-20: max_concurrent={max_concurrent}")
        raise ValidationError("max_concurrent must be between 1-20")

    # Remove duplicates while preserving order
    unique_names = list(dict.fromkeys(validated_names))

    await ctx.info(f"Starting batch repository details fetch: count={len(unique_names)}, max_concurrent={max_concurrent}")

    from .. import shared
    if not shared.github_client:
        await ctx.error("GitHub client not initialized")
        raise GitHubAPIError("GitHub client not initialized")

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create tasks for all repositories
    tasks = [
        fetch_single_repository_details(ctx, repo_name, shared.github_client, semaphore)
        for repo_name in unique_names
    ]

    try:
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_details = []
        failed_repositories = []

        for i, result in enumerate(results):
            repo_name = unique_names[i]

            if isinstance(result, Exception):
                await ctx.error(f"Task failed for {repo_name}: {str(result)}")
                failed_repositories.append(repo_name)
            elif result is None:
                failed_repositories.append(repo_name)
            else:
                successful_details.append(result)

        response = BatchRepositoryDetailsResponse(
            repository_details=successful_details,
            total_count=len(unique_names),
            success_count=len(successful_details),
            error_count=len(failed_repositories)
        )

        await ctx.info(
            f"Completed batch repository details fetch: "
            f"total={len(unique_names)}, success={len(successful_details)}, failed={len(failed_repositories)}"
        )

        return response

    except Exception as e:
        await ctx.error(f"Batch repository details fetch failed: {str(e)}")
        raise GitHubAPIError(f"Batch repository details fetch failed: {str(e)}")
