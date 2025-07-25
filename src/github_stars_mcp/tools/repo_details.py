"""Single repository details MCP tool."""

import structlog
from fastmcp import Context

from ..exceptions import GitHubAPIError, ValidationError
from ..models import RepositoryDetails
from ..shared import mcp
from .batch_repo_details import fetch_single_repository_details
import asyncio

# Get structured logger
logger = structlog.get_logger(__name__)


def validate_repository_name(repository_name: str) -> str:
    """Validate repository name format (owner/repo)."""
    if not repository_name:
        raise ValueError("Repository name cannot be empty")
    
    if '/' not in repository_name:
        raise ValueError("Repository name must be in format 'owner/repo'")
    
    parts = repository_name.split('/')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Repository name must be in format 'owner/repo'")
    
    return repository_name.strip()


@mcp.tool
async def get_repo_details(
    ctx: Context,
    repo_id: str
) -> RepositoryDetails:
    """
    为一个指定的 GitHub 仓库检索其详细信息，包括 README.md 文件的纯文本内容。当需要深入了解某一个特定项目时，或者当用户明确询问关于单个项目的信息时，使用此工具。
    """
    try:

        await ctx.info(f"Fetching details for repository: {repo_id}")
        
        # Create semaphore for consistency with batch function
        semaphore = asyncio.Semaphore(1)
        
        # Use the existing fetch function from batch_repo_details
        from .. import shared
        result = await fetch_single_repository_details(
            ctx, repo_id, shared.github_client, semaphore
        )
        
        if result is None:
            raise GitHubAPIError(f"Failed to fetch details for repository: {repo_id}")
        
        await ctx.info(f"Successfully fetched details for {repo_id}")
        return result
        
    except ValueError as e:
        await ctx.error(f"Invalid repository name: {str(e)}")
        raise ValidationError(f"Invalid repository name: {str(e)}")
    except GitHubAPIError:
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error fetching repository details: {str(e)}")
        raise GitHubAPIError(f"Failed to fetch repository details: {str(e)}")