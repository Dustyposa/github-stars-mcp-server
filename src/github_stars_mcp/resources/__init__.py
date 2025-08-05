"""MCP resources implementation package.

This package contains all MCP resource implementations for the GitHub Stars
MCP Server, including user information and repository data resources.
"""

# Import all MCP resources to register them
from . import user_info

__all__ = ["user_info"]
