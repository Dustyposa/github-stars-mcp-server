"""MCP server main entry point.

This module implements the FastMCP server with all registered tools
and handles the main server lifecycle.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, Optional, List

import structlog
from cachetools import TTLCache
from cachetools_async import cached
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator

from .config import settings
from .exceptions import (
    GitHubStarsMCPError,
    ConfigurationError,
    CacheError,
    GitHubAPIError,
    ValidationError,
)
from .models import Repository
from .utils.github_client import GitHubClient
from .shared import mcp, api_cache, github_client

# Import tools to register them with the MCP server
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


class StarredRepositoriesResponse(BaseModel):
    """用户收藏仓库列表响应模型。"""
    repositories: List[Repository] = Field(description="仓库列表")
    total_count: int = Field(description="总数量")
    has_more: bool = Field(description="是否还有更多数据")
    next_cursor: Optional[str] = Field(default=None, description="下一页游标")


# GetStarredRepositoriesParams is now defined in tools/timeline_analyzer.py


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


# get_user_starred_repositories tool is now defined in tools/timeline_analyzer.py


async def initialize_server() -> None:
    """Initialize the MCP server and its dependencies."""
    from .shared import github_client
    
    try:
        # Validate configuration
        if not settings.github_token:
            raise ConfigurationError(
                "GitHub token is required. Please set GITHUB_TOKEN environment variable."
            )
        
        # Initialize GitHub client
        import github_stars_mcp.shared as shared
        shared.github_client = GitHubClient(
            token=settings.github_token,
            cache=api_cache
        )
        
        logger.info(
            "MCP server initialized successfully",
            cache_max_size=api_cache.maxsize,
            cache_ttl=300,
            log_level=settings.log_level
        )
    
    except Exception as e:
        logger.error("Failed to initialize MCP server", error=str(e))
        raise


async def shutdown_server() -> None:
    """Clean up resources when shutting down the server."""
    global github_client
    
    try:
        # Close GitHub client if it exists
        if github_client:
            await github_client.close()
            github_client = None
        
        # Clear cache
        api_cache.clear()
        
        logger.info("MCP server shutdown completed")
    
    except Exception as e:
        logger.error("Error during server shutdown", error=str(e))


# Note: Exception handling is done through middleware in FastMCP
# Custom exceptions will be automatically handled by the framework


# Note: FastMCP handles server lifecycle automatically
# Custom initialization can be done in tool functions as needed
logger.info("GitHub Stars MCP Server initialized")

# Initialize GitHub client if token is available
if settings.github_token:
    from .utils.github_client import GitHubClient
    from . import shared
    shared.github_client = GitHubClient(settings.github_token)
    logger.info("GitHub client initialized successfully")
else:
    logger.warning("No GitHub token provided, some features may be limited")

# Initialize cache if Redis URL is provided
if hasattr(settings, 'redis_url') and settings.redis_url:
    logger.info(f"Redis cache configured at {settings.redis_url}")
else:
    logger.info("No Redis URL provided, using in-memory cache")


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