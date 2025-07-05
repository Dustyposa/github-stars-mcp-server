"""Timeline analysis MCP tool."""

from datetime import datetime
from typing import List, Dict, Any, Optional

import structlog
from fastmcp import Context

from ..models import Repository, StarredRepositoriesResponse
from ..exceptions import GitHubAPIError, ValidationError
from ..shared import mcp

# Get structured logger
logger = structlog.get_logger(__name__)


def validate_username(username: str) -> str:
    """Validate GitHub username."""
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
    if len(username) > 39:
        raise ValueError("Username length cannot exceed 39 characters")
    return username.strip()


@mcp.tool
async def get_user_starred_repositories(
    ctx: Context,
    username: Optional[str] = None,
    limit: int = 100,
    cursor: Optional[str] = None
) -> StarredRepositoriesResponse:
    """Get starred repositories for a specified GitHub user. If username is not provided, get starred repositories for the current authenticated user."""
    
    # If no username provided, get current user info
    if username is None:
        from .. import shared
        if not shared.github_client:
            await ctx.error("GitHub client not initialized")
            raise GitHubAPIError("GitHub client not initialized")
        
        try:
            current_user = await shared.github_client.get_current_user()
            if not current_user or not current_user.get("login"):
                await ctx.error("Unable to get current user info")
                raise GitHubAPIError("Unable to get current user info")
            username = current_user["login"]
            await ctx.info(f"Using current authenticated user: {username}")
        except Exception as e:
            await ctx.error(f"Failed to get current user info: {str(e)}")
            raise GitHubAPIError(f"Failed to get current user info: {str(e)}")
    else:
        try:
            username = validate_username(username)
        except ValueError as e:
            await ctx.error(f"Parameter validation failed: {str(e)}")
            raise ValidationError(str(e))
    
    if limit < 1 or limit > 100:
        await ctx.error(f"limit parameter must be between 1-100: limit={limit}")
        raise ValidationError("limit parameter must be between 1-100")
    
    await ctx.info(f"Starting to fetch user starred repositories: username={username}, limit={limit}, cursor={cursor}")
    
    from .. import shared
    if not shared.github_client:
        await ctx.error("GitHub client not initialized")
        raise GitHubAPIError("GitHub client not initialized")
    
    try:
        # Call GitHub client to get starred repositories with cursor support
        starred_data = await shared.github_client.get_user_starred_repositories(
            username=username,
            cursor=cursor
        )

        edges = starred_data.get("edges", [])

        logger.info(
            "Completed fetching starred repositories",
            username=username,
            total_repos=len(edges),
        )
        repositories = []
        for repo_data in edges:
            try:
                node = repo_data.get("node", {})
                starred_at_str = repo_data.get("starredAt")
                starred_at = (
                    datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))
                    if starred_at_str
                    else None
                )
                name_with_owner: str = node["nameWithOwner"]

                name, owner = name_with_owner.split("/", maxsplit=1)
                repo_dict = {
                    "nameWithOwner": name_with_owner,
                    "name": name,
                    "owner": owner,
                    "description": node.get("description"),
                    "stargazerCount": node.get("stargazerCount"),
                    "url": node.get("url"),
                    "primaryLanguage": node["primaryLanguage"].get("name") if node.get("primaryLanguage", {}) else None,
                    "starredAt": starred_at,
                    "pushedAt": node.get("pushedAt"),
                    "diskUsage": node.get("diskUsage"),
                    "repositoryTopics": [topic["topic"]["name"] for topic in node.get("repositoryTopics", {}).get("nodes", [])],
                    "languages": [
                        lang["node"]["name"]
                        for lang in node.get("languages", {}).get("edges", [])
                    ]
                }

                repo = Repository.model_validate(repo_dict)
                repositories.append(repo)
            except Exception as e:
                await ctx.info(f"Failed to parse repository data: {str(e)}")
                await ctx.info(f"node data: {node}")
                continue
        page_info = starred_data["pageInfo"]
        has_more, next_cursor = page_info.get("hasNextPage"), page_info.get("endCursor")

        response = StarredRepositoriesResponse(
            repositories=repositories,
            total_count=len(repositories),
            has_more=has_more,
            next_cursor=next_cursor
        )
        
        await ctx.info(f"Successfully fetched user starred repositories: username={username}, count={len(repositories)}, has_more={has_more}")
        await ctx.info(response)

        return response
    
    except GitHubAPIError:
        raise
    except Exception as e:
        await ctx.error(f"Failed to fetch user starred repositories: error={str(e)}, username={username}")
        raise GitHubAPIError(f"Failed to fetch user starred repositories: {str(e)}")

