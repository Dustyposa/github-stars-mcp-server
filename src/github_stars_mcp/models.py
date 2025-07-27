"""Data models for GitHub Stars MCP Server."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class StartedRepository(BaseModel):
    """GitHub repository model."""
    model_config = ConfigDict(populate_by_name=True)

    repo_id :str = Field(description="Repository ID", alias="id")
    name_with_owner: str = Field(alias='nameWithOwner', description="Repository full name (owner/repo)")
    name: str = Field(description="Repository name")
    owner: str = Field(description="Repository owner")
    description: Optional[str] = Field(default=None, description="Repository description")
    stargazer_count: int = Field(alias='stargazerCount', description="Number of stars")
    url: str = Field(description="Repository URL")
    primary_language: Optional[str] = Field(default=None, alias='primaryLanguage', description="Primary programming language")
    starred_at: Optional[datetime] = Field(default=None, alias='starredAt', description="Time when starred")
    pushed_at: Optional[datetime] = Field(default=None, alias='pushedAt', description="Last push time")
    disk_usage: Optional[int] = Field(default=None, alias='diskUsage', description="Repository disk usage in KB")
    repository_topics: list[str] = Field(default=[], alias='repositoryTopics', description="Repository topics")
    languages: list[str] = Field(default=[], description="Programming languages used in the repository")

class StartedRepoWithReadme(StartedRepository):
    """GitHub repository model with README content."""
    model_config = ConfigDict(populate_by_name=True)

    readme_content: Optional[str] = Field(default=None, description="Repository README content")

class StarredRepositoriesResponse(BaseModel):
    """Response model for starred repositories."""
    model_config = ConfigDict(populate_by_name=True)
    
    repositories: List[StartedRepository] = Field(description="List of starred repositories")
    total_count: int = Field(description="Total count of starred repositories")
    has_next_page: bool = Field(default=False, description="Whether there are more pages")
    end_cursor: Optional[str] = Field(default=None, description="End cursor for pagination")

class StarredRepositoriesWithReadmeResponse(BaseModel):
    """Response model for starred repositories with readme."""

    model_config = ConfigDict(populate_by_name=True)

    repositories: List[StartedRepoWithReadme] = Field(
        description="List of starred repositories"
    )
    total_count: int = Field(description="Total count of starred repositories")



class RepositoryDetails(BaseModel):
    """Detailed repository information including README content."""
    model_config = ConfigDict(populate_by_name=True)
    
    readme_content: Optional[str] = Field(default=None, description="README content")


class BatchRepositoryDetailsResponse(BaseModel):
    """Response model for batch repository details."""
    model_config = ConfigDict(populate_by_name=True)
    data : dict[str, RepositoryDetails] = Field(description="List of repository details")


class LanguageStats(BaseModel):
    """Programming language statistics."""
    model_config = ConfigDict(populate_by_name=True)
    
    language: str = Field(description="Programming language name")
    count: int = Field(description="Number of repositories using this language")
    percentage: float = Field(description="Percentage of total repositories")


class TopicStats(BaseModel):
    """Repository topic statistics."""
    model_config = ConfigDict(populate_by_name=True)
    
    topic: str = Field(description="Topic name")
    count: int = Field(description="Number of repositories with this topic")
    percentage: float = Field(description="Percentage of total repositories")


class StarStats(BaseModel):
    """Star count statistics."""
    model_config = ConfigDict(populate_by_name=True)
    
    total_stars: int = Field(description="Total number of stars across all repositories")
    average_stars: float = Field(description="Average stars per repository")
    median_stars: float = Field(description="Median stars per repository")
    max_stars: int = Field(description="Maximum stars in a single repository")
    min_stars: int = Field(description="Minimum stars in a single repository")


class AnalysisBundle(BaseModel):
    """Comprehensive analysis bundle for starred repositories."""
    model_config = ConfigDict(populate_by_name=True)
    
    username: str = Field(description="GitHub username")
    total_repositories: int = Field(description="Total number of starred repositories")
    repositories: List[RepositoryDetails] = Field(description="Detailed repository information")
    language_distribution: List[LanguageStats] = Field(description="Programming language distribution")
    topic_distribution: List[TopicStats] = Field(description="Topic distribution")
    star_statistics: StarStats = Field(description="Star count statistics")
    analysis_timestamp: datetime = Field(description="When the analysis was performed")
    processing_summary: Dict[str, Any] = Field(description="Processing summary and metadata")