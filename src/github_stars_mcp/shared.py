"""Shared instances and resources.

This module contains shared instances that need to be accessed by multiple modules
to avoid circular import issues.
"""

from typing import Optional
from cachetools import TTLCache
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("GitHub Stars MCP Server")

# Initialize cache
api_cache = TTLCache(maxsize=128, ttl=300)

# Global GitHub client instance (will be initialized in server.py)
github_client: Optional[object] = None