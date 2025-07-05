"""Pydantic data models for GitHub Stars MCP Server.

This module defines all data models used for GitHub API responses,
MCP tool inputs/outputs, and internal data structures.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class Repository(BaseModel):
    """GitHub仓库数据模型。
    
    与GitHub GraphQL API响应结构匹配的仓库模型。
    """
    model_config = ConfigDict(populate_by_name=True)
    
    name_with_owner: str = Field(alias='nameWithOwner', description="仓库的完整名称（所有者/仓库名）")
    description: Optional[str] = Field(default=None, description="仓库描述")
    stargazer_count: int = Field(alias='stargazerCount', description="星标数量")
    url: str = Field(description="仓库URL")
    primary_language: Optional[Dict[str, Any]] = Field(default=None, alias='primaryLanguage', description="主要编程语言")
    starred_at: Optional[datetime] = Field(default=None, alias='starredAt', description="加星时间")
    is_private: Optional[bool] = Field(default=None, alias='isPrivate', description="是否为私有仓库")
    is_fork: Optional[bool] = Field(default=None, alias='isFork', description="是否为分叉仓库")
    is_archived: Optional[bool] = Field(default=None, alias='isArchived', description="是否已归档")
    owner: Optional[Dict[str, Any]] = Field(default=None, description="仓库所有者信息")
    created_at: Optional[datetime] = Field(default=None, alias='createdAt', description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, alias='updatedAt', description="更新时间")
    pushed_at: Optional[datetime] = Field(default=None, alias='pushedAt', description="最后推送时间")


class User(BaseModel):
    """GitHub用户数据模型。
    
    与GitHub GraphQL API响应结构匹配的用户模型。
    """
    model_config = ConfigDict(populate_by_name=True)
    
    login: str = Field(description="用户登录名")
    name: Optional[str] = Field(default=None, description="用户显示名称")
    avatar_url: str = Field(alias='avatarUrl', description="用户头像URL")
    bio: Optional[str] = Field(default=None, description="用户简介")
    location: Optional[str] = Field(default=None, description="用户位置")
    company: Optional[str] = Field(default=None, description="用户公司")
    email: Optional[str] = Field(default=None, description="用户邮箱")
    public_repos: Optional[int] = Field(default=None, alias='publicRepos', description="公开仓库数量")
    followers: Optional[int] = Field(default=None, description="关注者数量")
    following: Optional[int] = Field(default=None, description="关注数量")
    created_at: Optional[datetime] = Field(default=None, alias='createdAt', description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, alias='updatedAt', description="更新时间")


class StarredRepository(BaseModel):
    """用户加星的仓库数据模型。
    
    包含仓库信息和加星时间的组合模型。
    """
    model_config = ConfigDict(populate_by_name=True)
    
    repository: Repository = Field(description="仓库信息")
    starred_at: datetime = Field(alias='starredAt', description="加星时间")


class PageInfo(BaseModel):
    """分页信息数据模型。
    
    用于GraphQL分页查询的游标信息。
    """
    model_config = ConfigDict(populate_by_name=True)
    
    has_next_page: bool = Field(alias='hasNextPage', description="是否有下一页")
    has_previous_page: bool = Field(alias='hasPreviousPage', description="是否有上一页")
    start_cursor: Optional[str] = Field(default=None, alias='startCursor', description="起始游标")
    end_cursor: Optional[str] = Field(default=None, alias='endCursor', description="结束游标")


class StarredRepositoriesResponse(BaseModel):
    """用户收藏仓库列表响应模型。
    
    用于封装从GitHub API获取的用户收藏仓库数据。
    """
    model_config = ConfigDict(populate_by_name=True)
    
    repositories: List[Repository] = Field(description="仓库列表")
    total_count: int = Field(description="总数量")
    has_more: bool = Field(default=False, description="是否还有更多数据")
    next_cursor: Optional[str] = Field(default=None, description="下一页游标")