"""Shared instances and resources for GitHub Stars MCP Server."""

import sys
import logging
from typing import Optional

import structlog
from cachetools import TTLCache

# Redirect stdout to stderr before importing FastMCP
_original_stdout = sys.stdout
sys.stdout = sys.stderr

from fastmcp import FastMCP

# Restore stdout after FastMCP import
sys.stdout = _original_stdout

# Configure logging immediately when module is imported
def _configure_logging():
    """Configure logging for the application, directing all output to a file."""

    # 假设的 settings 对象，请替换为您自己的配置加载方式
    class MockSettings:
        log_level = "DEBUG"

    settings = MockSettings()

    # 只配置一次
    if logging.getLogger().handlers:
        return

    # [核心修复] 将所有日志输出到文件，而不是 stderr
    file_handler = logging.FileHandler("mcp_server_debug.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(name)s - %(levelname)s - %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 配置 structlog 以使用标准 logging
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
            # 使用更适合文件输出的 KeyValueRenderer 或 JSONRenderer
            structlog.processors.KeyValueRenderer(
                key_order=["timestamp", "level", "event", "logger"]
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 静默其他嘈杂的日志记录器
    fastmcp_silent_loggers = ["fastmcp.transport", "fastmcp.protocol"]
    for logger_name in fastmcp_silent_loggers:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL + 1)

    logging.getLogger("github_stars_mcp").info(
        "Logging configured to file 'mcp_server_debug.log'"
    )


# 立即执行配置
_configure_logging()


from github_stars_mcp.utils.github_client import GitHubClient
from github_stars_mcp.cache.file_cache import FileCache

# FastMCP server instance
mcp = FastMCP("GitHub Stars MCP Server")

# API response cache (L1 cache)
api_cache = TTLCache(maxsize=128, ttl=300)

# File cache instance (L2 cache)
file_cache: Optional[FileCache] = None

# GitHub client instance
github_client: Optional[GitHubClient] = None


async def initialize_file_cache():
    """Initialize file cache."""
    global file_cache
    try:
        from .config import settings
        import structlog
        
        logger = structlog.get_logger(__name__)
        file_cache = FileCache(cache_dir=settings.cache_dir)
        logger.info("File cache initialized", cache_dir=settings.cache_dir)
    except Exception as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error("Failed to initialize file cache", error=str(e))
        file_cache = None


async def initialize_github_client():
    """Initialize GitHub client."""
    global github_client
    try:
        from .config import settings
        import structlog
        
        logger = structlog.get_logger(__name__)
        github_client = GitHubClient(settings.github_token)
        logger.info("GitHub client initialized")
    except Exception as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error("Failed to initialize GitHub client", error=str(e))
        github_client = None