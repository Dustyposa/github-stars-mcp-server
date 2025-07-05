"""Data models for GitHub Stars MCP Server."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class Repository(BaseModel):
    """GitHub repository model."""
    model_config = ConfigDict(populate_by_name=True)
    
    name_with_owner: str = Field(alias='nameWithOwner', description="Repository full name (owner/repo)")
    description: Optional[str] = Field(default=None, description="Repository description")
    stargazer_count: int = Field(alias='stargazerCount', description="Number of stars")
    url: str = Field(description="Repository URL")
    primary_language: Optional[str] = Field(default=None, alias='primaryLanguage', description="Primary programming language")
    starred_at: Optional[datetime] = Field(default=None, alias='starredAt', description="Time when starred")
    owner: str = Field(default=..., description="Repository owner information")
    name: str = Field(default=..., description="Repository name")
    pushed_at: Optional[datetime] = Field(default=None, alias='pushedAt', description="Last push time")
    disk_usage: Optional[int] = Field(default=None, alias='diskUsage', description="Repository disk usage in KB")
    repository_topics: list[str] = Field(default=[], alias='repositoryTopics', description="Repository topics")
    languages: list[str] = Field(default=[], description="Programming languages used in the repository")

class StarredRepositoriesResponse(BaseModel):
    """Response model for starred repositories."""
    model_config = ConfigDict(populate_by_name=True)
    
    repositories: List[Repository] = Field(description="List of repositories")
    total_count: int = Field(description="Total count")
    has_more: bool = Field(default=False, description="Whether there is more data")
    next_cursor: Optional[str] = Field(default=None, description="Next page cursor")