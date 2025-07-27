"""Tool for retrieving user's starred repositories list."""

import structlog
from fastmcp import Context

from ..common.error_handlers import handle_github_api_errors
from ..common.github_helpers import ensure_github_client, safe_github_request
from ..common.logging_helpers import log_function_call
from ..common.validators import validate_github_username
from ..models import StarredRepositoriesResponse, StartedRepository
from ..shared import mcp

logger = structlog.get_logger(__name__)





def _parse_repository_data(edge: dict) -> StartedRepository:
    """Parse repository data from GitHub API response.

    Args:
        edge: Repository edge from GitHub GraphQL response

    Returns:
        StartedRepository object
    """
    repo_data = edge["node"]
    name_with_owner: str = repo_data["nameWithOwner"]
    name, owner = name_with_owner.split("/", maxsplit=1)

    return StartedRepository(
        id=repo_data["id"],
        nameWithOwner=name_with_owner,
        name=name,
        owner=owner,
        description=repo_data.get("description"),
        stargazerCount=repo_data.get("stargazerCount"),
        url=repo_data.get("url"),
        primaryLanguage=(
            repo_data["primaryLanguage"].get("name")
            if repo_data.get("primaryLanguage")
            else None
        ),
        starredAt=edge.get("starredAt"),
        pushedAt=repo_data.get("pushedAt"),
        diskUsage=repo_data.get("diskUsage"),
        repositoryTopics=[
            topic["topic"]["name"]
            for topic in repo_data.get("repositoryTopics", {}).get("nodes", [])
        ],
        languages=[
            lang["node"]["name"]
            for lang in repo_data.get("languages", {}).get("edges", [])
        ],
    )


@handle_github_api_errors("get starred repositories")
@log_function_call("get_user_starred_repositories_impl")
async def _get_user_starred_repositories_impl(
    ctx: Context, username: str = "", cursor: str = ""
) -> StarredRepositoriesResponse:
    """Internal implementation for getting starred repositories.

    This function contains the core logic that can be called from other tools.
    """
    from .. import shared

    # Validate username if provided
    if username:
        username = validate_github_username(username)

    # Ensure GitHub client is available
    github_client = ensure_github_client(shared.github_client)

    # Get starred repositories from GitHub API
    response = await safe_github_request(
        "get starred repositories",
        github_client.get_user_starred_repositories,
        username=username,
        cursor=cursor
    )

    # Parse repositories
    repositories = [
        _parse_repository_data(edge)
        for edge in response.get("edges", [])
    ]

    result = StarredRepositoriesResponse(
        repositories=repositories,
        total_count=response.get("totalCount", len(repositories)),
        has_next_page=response.get("pageInfo", {}).get("hasNextPage", False),
        end_cursor=response.get("pageInfo", {}).get("endCursor", ""),
    )

    await ctx.info(f"Retrieved {len(repositories)} starred repositories")
    return result


@mcp.tool
@log_function_call("get_user_starred_repositories")
async def get_user_starred_repositories(
    ctx: Context, username: str = "", cursor: str = ""
) -> StarredRepositoriesResponse:
    """Get a list of repositories starred by a user.

    Args:
        username: GitHub username to get starred repositories for. If empty, uses authenticated user.
        cursor: Pagination cursor for getting next page of results

    Returns:
        StarredRepositoriesResponse containing list of starred repositories with pagination info.

    Raises:
        AuthenticationError: If GitHub token is invalid or missing
        GitHubAPIError: If GitHub API request fails
        ValidationError: If username format is invalid
    """
    return await _get_user_starred_repositories_impl(ctx, username, cursor)
