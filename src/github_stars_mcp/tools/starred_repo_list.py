"""Tool for retrieving user's starred repositories list."""

import logging
from typing import List, Dict, Any

from fastmcp import Context
from pydantic import BaseModel, Field

from ..shared import mcp
from ..models import StartedRepository, StarredRepositoriesResponse
from ..exceptions import GitHubAPIError, AuthenticationError


logger = logging.getLogger(__name__)


class GetStarredRepoListRequest(BaseModel):
    """Request model for getting starred repositories list."""
    
    username: str = Field(
        description="GitHub username to get starred repositories for. If not provided, uses authenticated user.",
        default=""
    )
    limit: int = Field(
        description="Maximum number of repositories to return (1-100)",
        default=50,
        ge=1,
        le=100
    )
    cursor: str = Field(
        description="Pagination cursor for getting next page of results",
        default=""
    )


@mcp.tool
async def get_user_starred_repositories(
    ctx: Context,
    username: str = "",
    cursor: str = ""
) -> StarredRepositoriesResponse:
    """Get a list of repositories starred by a user.
    
    Args:
        username: GitHub username to get starred repositories for. If empty, uses authenticated user.
        limit: Maximum number of repositories to return (1-100, default: 50)
        cursor: Pagination cursor for getting next page of results
        
    Returns:
        Dict containing list of starred repositories with pagination info.
        
    Raises:
        AuthenticationError: If GitHub token is invalid or missing
        GitHubAPIError: If GitHub API request fails
    """


    try:

        from .. import shared

        if not shared.github_client:
            raise AuthenticationError("GitHub client not initialized")

        # Get starred repositories from GitHub API
        response = await shared.github_client.get_user_starred_repositories(
            username=username,
            cursor=cursor
        )
        
        # Convert to our model format
        repositories = []
        for edge in response.get("edges"):
            repo_data = edge["node"]
            name_with_owner: str = repo_data["nameWithOwner"]

            name, owner = name_with_owner.split("/", maxsplit=1)
            repo = StartedRepository(**{
                "id": repo_data["id"],
                "nameWithOwner": name_with_owner,
                "name": name,
                "owner": owner,
                "description": repo_data.get("description"),
                "stargazerCount": repo_data.get("stargazerCount"),
                "url": repo_data.get("url"),
                "primaryLanguage": repo_data["primaryLanguage"].get("name")
                if repo_data.get("primaryLanguage", {})
                else None,
                "starredAt": edge.get("starredAt"),
                "pushedAt": repo_data.get("pushedAt"),
                "diskUsage": repo_data.get("diskUsage"),
                "repositoryTopics": [
                    topic["topic"]["name"]
                    for topic in repo_data['repositoryTopics']["nodes"]
                ],
                "languages": [
                    lang["node"]["name"]
                    for lang in repo_data.get("languages", {}).get("edges", [])
                ],
            })
            repositories.append(repo)
        
        result = StarredRepositoriesResponse(
            repositories=repositories,
            total_count=response.get('totalCount', len(repositories)),
            has_next_page=response.get('pageInfo', {}).get('hasNextPage', False),
            end_cursor=response.get('pageInfo', {}).get('endCursor', '')
        )
        
        await ctx.info(f"Retrieved {len(repositories)} starred repositories")
        return result
        
    except AuthenticationError:
        await ctx.error("Authentication failed - check GitHub token")
        raise
    except GitHubAPIError as e:
        await ctx.error(f"GitHub API error: {str(e)}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error getting starred repositories: {str(e)}")
        raise GitHubAPIError(f"Failed to get starred repositories: {str(e)}")