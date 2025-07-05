"""Timeline analysis MCP tool.

This module implements the MCP tool for analyzing GitHub user starred
repositories timeline and providing insights into technology trends.
"""

import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import structlog
from cachetools_async import cached
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator

from ..models import Repository, StarredRepository, PageInfo
from ..exceptions import GitHubAPIError, ValidationError
from ..shared import mcp, api_cache, github_client

# Get structured logger
logger = structlog.get_logger(__name__)


class StarredRepositoriesResponse(BaseModel):
    """用户收藏仓库列表响应模型。"""
    repositories: List[Repository] = Field(description="仓库列表")
    total_count: int = Field(description="总数量")
    has_more: bool = Field(description="是否还有更多数据")
    next_cursor: Optional[str] = Field(default=None, description="下一页游标")


class TimelineAnalysis(BaseModel):
    """时间线分析结果模型。"""
    total_starred: int = Field(description="总收藏数量")
    languages_distribution: Dict[str, int] = Field(description="编程语言分布")
    monthly_activity: Dict[str, int] = Field(description="月度活动统计")
    top_repositories: List[Repository] = Field(description="热门仓库（按星数排序）")
    recent_activity: List[Repository] = Field(description="最近收藏的仓库")
    analysis_period: str = Field(description="分析时间段")


class GetStarredRepositoriesParams(BaseModel):
    """获取收藏仓库参数模型。"""
    username: str = Field(description="GitHub用户名")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="返回数量限制")
    cursor: Optional[str] = Field(default=None, description="分页游标")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError("用户名不能为空")
        if len(v) > 39:  # GitHub username max length
            raise ValueError("用户名长度不能超过39个字符")
        return v.strip()


class AnalyzeTimelineParams(BaseModel):
    """分析时间线参数模型。"""
    username: str = Field(description="GitHub用户名")
    days_back: Optional[int] = Field(default=365, ge=1, le=3650, description="分析天数（最多10年）")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError("用户名不能为空")
        if len(v) > 39:
            raise ValueError("用户名长度不能超过39个字符")
        return v.strip()


@mcp.tool
async def get_user_starred_repositories(
    ctx: Context,
    username: str,
    limit: int = 100,
    cursor: Optional[str] = None
) -> StarredRepositoriesResponse:
    """获取指定GitHub用户收藏的仓库列表。
    
    Args:
        username: GitHub用户名
        limit: 返回数量限制（1-1000）
        cursor: 分页游标，用于获取下一页数据
    
    Returns:
        StarredRepositoriesResponse: 包含仓库列表和分页信息的响应
    
    Raises:
        ValidationError: 参数验证失败
        GitHubAPIError: GitHub API调用失败
    """
    # 参数验证
    if not username or not username.strip():
        await ctx.error(f"用户名不能为空: username={username}")
        raise ValidationError("用户名不能为空")
    
    if len(username) > 39:
        await ctx.error(f"用户名长度不能超过39个字符: username={username}")
        raise ValidationError("用户名长度不能超过39个字符")
    
    if limit < 1 or limit > 1000:
        await ctx.error(f"limit参数必须在1-1000之间: limit={limit}")
        raise ValidationError("limit参数必须在1-1000之间")
    
    username = username.strip()
    
    await ctx.info(f"开始获取用户收藏仓库列表: username={username}, limit={limit}, cursor={cursor}")
    
    from .. import shared
    if not shared.github_client:
        await ctx.error("GitHub客户端未初始化")
        raise GitHubAPIError("GitHub客户端未初始化")
    
    try:
        # 调用GitHub客户端获取收藏仓库
        repositories_data = await shared.github_client.get_user_starred_repositories(
            username=username
        )
        
        # 解析响应数据
        repositories = []
        for repo_data in repositories_data:
            """
            repo_data: [{'cursor': 'Y3Vyc29yOnYyOpK5MjAyNS0wNy0wNFQxNjowODozNCswODowMM4j6Dv_',
                                                      'node': {'description': 'A '
                                                                              'powerful '
                                                                              'AI '
                                                                              'coding '
                                                                              'agent. '
                                                                              'Built '
                                                                              'for '
                                                                              'the '
                                                                              'terminal.',
                                                               'nameWithOwner': 'opencode-ai/opencode',
                                                               'primaryLanguage': {'color': '#00ADD8',
                                                                                   'name': 'Go'},
                                                               'stargazerCount': 6760,
                                                               'url': 'https://github.com/opencode-ai/opencode'},
                                                      'starredAt': '2025-07-04T08:08:34Z'}
                      """
            try:
                # 获取 node 字段中的仓库基本信息


                node = repo_data.get("node", {})
                if not  node.get("nameWithOwner"):
                    await ctx.info(
                        f"repo_date: {repo_data}"
                    )

                # 提取 starredAt 时间（来自 edge）
                starred_at_str = repo_data.get("starredAt")
                starred_at = (
                    datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))
                    if starred_at_str
                    else None
                )

                # 构造 Repository 所需的完整数据字典
                repo_dict = {
                    "nameWithOwner": node.get("nameWithOwner"),
                    "description": node.get("description"),
                    "stargazerCount": node.get("stargazerCount"),
                    "url": node.get("url"),
                    "primaryLanguage": node.get("primaryLanguage"),
                    "starredAt": starred_at,
                    # 其他字段如果存在也可以映射，比如：
                    "isPrivate": node.get("isPrivate"),
                    "isFork": node.get("isFork"),
                    "isArchived": node.get("isArchived"),
                    "owner": node.get("owner"),
                    "createdAt": node.get("createdAt"),
                    "updatedAt": node.get("updatedAt"),
                    "pushedAt": node.get("pushedAt"),
                }

                # 使用 pydantic 模型构建对象
                repo = Repository.model_validate(repo_dict)

                repositories.append(repo)
            except Exception as e:
                await ctx.info(f"解析仓库数据失败: error={str(e)}, repo_data={repo_data}")
                continue
        
        # 由于GitHubClient.get_user_starred_repositories已经处理了分页，这里不需要分页信息
        has_more = False
        next_cursor = None
        
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

