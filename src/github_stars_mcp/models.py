"""Data models for GitHub Stars MCP Server."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StartedRepository(BaseModel):
    """GitHub repository model."""

    model_config = ConfigDict(populate_by_name=True)

    repo_id: str = Field(description="Repository ID", alias="id")
    name_with_owner: str = Field(
        alias="nameWithOwner", description="Repository full name (owner/repo)"
    )
    name: str = Field(description="Repository name")
    owner: str = Field(description="Repository owner")
    description: str | None = Field(default=None, description="Repository description")
    stargazer_count: int = Field(alias="stargazerCount", description="Number of stars")
    url: str = Field(description="Repository URL")
    primary_language: str | None = Field(
        default=None,
        alias="primaryLanguage",
        description="Primary programming language",
    )
    starred_at: datetime | None = Field(
        default=None, alias="starredAt", description="Time when starred"
    )
    pushed_at: datetime | None = Field(
        default=None, alias="pushedAt", description="Last push time"
    )
    disk_usage: int | None = Field(
        default=None, alias="diskUsage", description="Repository disk usage in KB"
    )
    repository_topics: list[str] = Field(
        default=[], alias="repositoryTopics", description="Repository topics"
    )
    languages: list[str] = Field(
        default=[], description="Programming languages used in the repository"
    )


class StartedRepoWithReadme(StartedRepository):
    """GitHub repository model with README content."""

    model_config = ConfigDict(populate_by_name=True)

    readme_content: str | None = Field(
        default=None, description="Repository README content"
    )


class StarredRepositoriesResponse(BaseModel):
    """Response model for starred repositories."""

    model_config = ConfigDict(populate_by_name=True)

    repositories: list[StartedRepository] = Field(
        description="List of starred repositories"
    )
    total_count: int = Field(description="Total count of starred repositories")
    has_next_page: bool = Field(
        default=False, description="Whether there are more pages"
    )
    end_cursor: str | None = Field(
        default=None, description="End cursor for pagination"
    )


class StarredRepositoriesWithReadmeResponse(BaseModel):
    """Response model for starred repositories with readme."""

    model_config = ConfigDict(populate_by_name=True)

    repositories: list[StartedRepoWithReadme] = Field(
        description="List of starred repositories"
    )
    total_count: int = Field(description="Total count of starred repositories")


class RepositoryDetails(BaseModel):
    """Detailed repository information including README content."""

    model_config = ConfigDict(populate_by_name=True)

    readme_content: str | None = Field(default=None, description="README content")


class BatchRepositoryDetailsResponse(BaseModel):
    """Response model for batch repository details."""

    model_config = ConfigDict(populate_by_name=True)
    data: dict[str, RepositoryDetails] = Field(description="List of repository details")


