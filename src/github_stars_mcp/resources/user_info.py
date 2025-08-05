"""User information MCP resource."""

import structlog
from fastmcp import Context

from ..common.error_handlers import handle_github_api_errors
from ..common.github_helpers import ensure_github_client
from ..common.logging_helpers import log_function_call
from ..exceptions import AuthenticationError
from ..shared import mcp
from .. import shared

# Get structured logger
logger = structlog.get_logger(__name__)


@handle_github_api_errors("get current user info")
@log_function_call("get_current_user_info")
async def _get_current_user_info_impl(ctx: Context) -> dict:
    """Internal implementation for getting current user information.

    Args:
        ctx: FastMCP context

    Returns:
        Dictionary containing current user information

    Raises:
        AuthenticationError: If user authentication fails
    """
    github_client = ensure_github_client(shared.github_client)

    user_data = await github_client.get_current_user()
    if not user_data:
        logger.error("Failed to get current user information")
        raise AuthenticationError("Unable to retrieve current user information")

    logger.info(
        "Current user info retrieved successfully",
        username=user_data.get("login"),
        user_id=user_data.get("id")
    )

    return {
        "username": user_data.get("login"),
        "name": user_data.get("name"),
        "email": user_data.get("email"),
        "avatar_url": user_data.get("avatarUrl"),
        "bio": user_data.get("bio"),
        "company": user_data.get("company"),
        "location": user_data.get("location"),
        "public_repos": user_data.get("repositories", {}).get("totalCount"),
        "followers": user_data.get("followers", {}).get("totalCount"),
        "following": user_data.get("following", {}).get("totalCount"),
        "created_at": user_data.get("createdAt")
    }


@mcp.resource("github://user/current")
@log_function_call("get_current_user_resource")
async def get_current_user_resource(ctx: Context) -> str:
    """Get current authenticated user information as a resource.

    This resource provides information about the currently authenticated GitHub user,
    including username, profile details, and basic statistics.

    Returns:
        JSON string containing current user information
    """
    import json

    user_info = await _get_current_user_info_impl(ctx)

    # Format as readable JSON
    return json.dumps(user_info, indent=2, ensure_ascii=False)
