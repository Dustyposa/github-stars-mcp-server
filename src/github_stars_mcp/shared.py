"""Shared instances and resources for GitHub Stars MCP Server."""

from typing import Optional
from cachetools import TTLCache
from fastmcp import FastMCP

from github_stars_mcp.utils.github_client import GitHubClient

# FastMCP server instance
mcp = FastMCP("GitHub Stars MCP Server")

# API response cache
api_cache = TTLCache(maxsize=128, ttl=300)

# GitHub client instance
github_client: Optional[GitHubClient] = None