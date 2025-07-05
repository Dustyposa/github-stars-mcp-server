"""Timeline analysis MCP tool."""

from datetime import datetime
from os.path import split
from typing import List, Dict, Any, Optional

import structlog
from fastmcp import Context

from ..models import Repository, StarredRepositoriesResponse
from ..exceptions import GitHubAPIError, ValidationError
from ..shared import mcp

# Get structured logger
logger = structlog.get_logger(__name__)





def validate_username(username: str) -> str:
    """Validate GitHub username."""
    if not username or not username.strip():
        raise ValueError("用户名不能为空")
    if len(username) > 39:
        raise ValueError("用户名长度不能超过39个字符")
    return username.strip()


@mcp.tool
async def get_user_starred_repositories(
    ctx: Context,
    username: Optional[str] = None,
    limit: int = 100,
    cursor: Optional[str] = None
) -> StarredRepositoriesResponse:
    """获取指定GitHub用户收藏的仓库列表。如果未提供username，则获取当前认证用户的收藏仓库。"""
    
    # 如果没有提供username，获取当前用户信息
    if username is None:
        from .. import shared
        if not shared.github_client:
            await ctx.error("GitHub客户端未初始化")
            raise GitHubAPIError("GitHub客户端未初始化")
        
        try:
            current_user = await shared.github_client.get_current_user()
            if not current_user or not current_user.get("login"):
                await ctx.error("无法获取当前用户信息")
                raise GitHubAPIError("无法获取当前用户信息")
            username = current_user["login"]
            await ctx.info(f"使用当前认证用户: {username}")
        except Exception as e:
            await ctx.error(f"获取当前用户信息失败: {str(e)}")
            raise GitHubAPIError(f"获取当前用户信息失败: {str(e)}")
    else:
        try:
            username = validate_username(username)
        except ValueError as e:
            await ctx.error(f"参数验证失败: {str(e)}")
            raise ValidationError(str(e))
    
    if limit < 1 or limit > 100:
        await ctx.error(f"limit参数必须在1-100之间: limit={limit}")
        raise ValidationError("limit参数必须在1-100之间")
    
    await ctx.info(f"开始获取用户收藏仓库列表: username={username}, limit={limit}, cursor={cursor}")
    
    from .. import shared
    if not shared.github_client:
        await ctx.error("GitHub客户端未初始化")
        raise GitHubAPIError("GitHub客户端未初始化")
    
    try:
        # 调用GitHub客户端获取收藏仓库
        starred_data = await shared.github_client.get_user_starred_repositories(
            username=username
        )

        edges = starred_data.get("edges", [])

        logger.info(
            "Completed fetching starred repositories",
            username=username,
            total_repos=len(edges),
        )
        repositories = []
        for repo_data in edges:
            try:
                node = repo_data.get("node", {})
                starred_at_str = repo_data.get("starredAt")
                starred_at = (
                    datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))
                    if starred_at_str
                    else None
                )
                name_with_owner: str = node["nameWithOwner"]

                name, owner = name_with_owner.split("/", maxsplit=1)
                repo_dict = {
                    "nameWithOwner": name_with_owner,
                    "name": name,
                    "owner": owner,
                    "description": node.get("description"),
                    "stargazerCount": node.get("stargazerCount"),
                    "url": node.get("url"),
                    "primaryLanguage": node["primaryLanguage"].get("name") if node.get("primaryLanguage", {}) else None,
                    "starredAt": starred_at,
                    "pushedAt": node.get("pushedAt"),
                    "diskUsage": node.get("diskUsage"),
                    "repositoryTopics": [topic["topic"]["name"] for topic in node.get("repositoryTopics", {}).get("nodes", [])],
                    "languages": [
                        lang["node"]["name"]
                        for lang in node.get("languages", {}).get("edges", [])
                    ]
                }

                repo = Repository.model_validate(repo_dict)
                repositories.append(repo)
            except Exception as e:
                await ctx.info(f"解析仓库数据失败: {str(e)}")
                await ctx.info(f"node data: {node}")
                continue
        page_info = starred_data["pageInfo"]
        has_more, next_cursor = page_info.get("hasNextPage"), page_info.get("endCursor")

        response = StarredRepositoriesResponse(
            repositories=repositories,
            total_count=len(repositories),
            has_more=has_more,
            next_cursor=next_cursor
        )
        
        await ctx.info(f"成功获取用户收藏仓库列表: username={username}, count={len(repositories)}, has_more={has_more}")
        await ctx.info(response)

        # 返回可序列化的字典而不是 Pydantic 模型对象
        return response
    
    except GitHubAPIError:
        raise
    except Exception as e:
        await ctx.error(f"获取用户收藏仓库失败: error={str(e)}, username={username}")
        raise GitHubAPIError(f"获取用户收藏仓库失败: {str(e)}")

