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
    repository_name: str
) -> RepositoryDetails:
    """Fetch single repository details including README content.

    Args:
        repository_name: Repository name in format 'owner/repo'

    Returns:
        RepositoryDetails with repository information and README content

    Raises:
        GitHubAPIError: If GitHub API request fails
        ValidationError: If repository name format is invalid
    """
    try:
        # Validate repository name
        validated_name = validate_repository_name(repository_name)
        
        await ctx.info(f"Fetching details for repository: {validated_name}")
        
        # Create semaphore for consistency with batch function
        semaphore = asyncio.Semaphore(1)
        
        # Use the existing fetch function from batch_repo_details
        from .. import shared
        result = await fetch_single_repository_details(
            ctx, validated_name, shared.github_client, semaphore
        )
        
        if result is None:
            raise GitHubAPIError(f"Failed to fetch details for repository: {validated_name}")
        
        await ctx.info(f"Successfully fetched details for {validated_name}")
        return result
        
    except ValueError as e:
        await ctx.error(f"Invalid repository name: {str(e)}")
        raise ValidationError(f"Invalid repository name: {str(e)}")
    except GitHubAPIError:
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error fetching repository details: {str(e)}")
        raise GitHubAPIError(f"Failed to fetch repository details: {str(e)}")