"""MCP server main entry point."""

import logging
import sys
from typing import Any, Dict

import structlog
from fastmcp import Context
from pydantic import BaseModel, Field

from .config import settings
from .exceptions import ConfigurationError, CacheError, GitHubAPIError
from .utils.github_client import GitHubClient
from .shared import mcp, api_cache

# Import tools to register them
from . import tools


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Get structured logger
logger = structlog.get_logger(__name__)


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    version: str = "0.1.0"
    github_api_available: bool
    cache_size: int
    cache_max_size: int





@mcp.tool
async def health_check(ctx: Context) -> HealthStatus:
    """Perform a health check of the MCP server and its dependencies.
    
    Returns:
        HealthStatus: Current health status including GitHub API availability
                     and cache statistics.
    """
    await ctx.info("Performing health check")
    
    try:
        # Check GitHub API availability
        github_available = False
        from . import shared
        if shared.github_client:
            try:
                # Simple API call to check connectivity
                await shared.github_client.query(
                    "query { viewer { login } }",
                    variables={}
                )
                github_available = True
            except Exception as e:
                await ctx.warning(f"GitHub API check failed: {str(e)}")
                github_available = False
        
        health_status = HealthStatus(
            status="healthy" if github_available else "degraded",
            github_api_available=github_available,
            cache_size=len(api_cache),
            cache_max_size=api_cache.maxsize
        )
        return health_status.model_dump()
    
    except Exception as e:
        await ctx.error(f"Health check failed: {str(e)}")
        return HealthStatus(
            status="unhealthy",
            github_api_available=False,
            cache_size=0,
            cache_max_size=0
        )


@mcp.tool
async def clear_cache(ctx: Context) -> Dict[str, Any]:
    """Clear the API response cache.
    
    Returns:
        Dict containing the number of items cleared from cache.
    """
    await ctx.info("Clearing API cache")
    
    try:
        items_cleared = len(api_cache)
        api_cache.clear()
        
        await ctx.info("Cache cleared successfully")
        return {
            "status": "success",
            "items_cleared": items_cleared,
            "message": f"Cleared {items_cleared} items from cache"
        }
    
    except Exception as e:
        await ctx.error("Failed to clear cache")
        raise CacheError(f"Failed to clear cache: {str(e)}")

# Initialize GitHub client
if settings.github_token:
    from . import shared
    shared.github_client = GitHubClient(settings.github_token)
    logger.info("GitHub client initialized")
else:
    logger.warning("No GitHub token provided")


def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Set up logging level
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(message)s",
            stream=sys.stdout
        )
        
        logger.info(
            "GitHub Stars MCP Server starting",
            version="0.1.0",
            log_level=settings.log_level
        )
        
        # Run the MCP server
        mcp.run()
    
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()