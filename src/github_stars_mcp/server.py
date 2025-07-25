"""MCP server main entry point."""

import logging
import sys

# Redirect stdout to stderr immediately to prevent MCP protocol conflicts
_original_stdout = sys.stdout
sys.stdout = sys.stderr

import structlog

from .config import settings
from .exceptions import ConfigurationError
from .shared import mcp

# Restore stdout after imports
sys.stdout = _original_stdout

# Import tools to register them
from . import tools


# Logging is now configured in shared.py when the module is imported

# Get structured logger
logger = structlog.get_logger(__name__)
logger.info("GitHub Stars MCP Server module loaded", log_level=settings.log_level)


# Server tools removed - keeping only core repository analysis tools

# Async initialization function
async def initialize_server():
    """Initialize server components asynchronously."""
    from . import shared
    
    # Initialize file cache
    await shared.initialize_file_cache()
    
    # Initialize GitHub client
    if settings.github_token:
        await shared.initialize_github_client()
    else:
        logger.warning("No GitHub token provided")


# Initialize server components at module level
import asyncio

# Run initialization
try:
    loop = asyncio.get_running_loop()
    # If loop is already running, schedule the initialization
    asyncio.create_task(initialize_server())
except RuntimeError:
    # No running loop, create and run initialization
    asyncio.run(initialize_server())


def main() -> None:
    """Main entry point for the MCP server."""
    # Redirect stdout to stderr for MCP server execution
    sys.stdout = sys.stderr
    
    try:
        logger.info("Starting GitHub Stars MCP Server from main()", log_level=settings.log_level)
        
        # Run the MCP server
        mcp.run()
    
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()