"""Simple tests for MCP tools functionality."""

import pytest
from unittest.mock import patch, AsyncMock

from github_stars_mcp.models import (
    StarredRepositoriesResponse,
    StartedRepository,
    RepositoryDetails
)
from github_stars_mcp.tools.starred_repo_list import _parse_repository_data
from github_stars_mcp.exceptions import GitHubAPIError, RateLimitError


class TestDataParsing:
    """Test data parsing functionality."""

    def test_parse_repository_data_complete(self):
        """Test parsing repository data with all fields."""
        edge_data = {
            "starredAt": "2023-01-01T00:00:00Z",
            "node": {
                "id": "repo123",
                "nameWithOwner": "octocat/Hello-World",
                "description": "This your first repo!",
                "stargazerCount": 1420,
                "url": "https://github.com/octocat/Hello-World",
                "primaryLanguage": {"name": "Python"},
                "pushedAt": "2023-01-01T00:00:00Z",
                "diskUsage": 1024,
                "repositoryTopics": {
                    "nodes": [
                        {"topic": {"name": "python"}},
                        {"topic": {"name": "web"}}
                    ]
                },
                "languages": {
                    "edges": [
                        {"node": {"name": "Python"}},
                        {"node": {"name": "JavaScript"}}
                    ]
                }
            }
        }
        
        result = _parse_repository_data(edge_data)
        
        assert isinstance(result, StartedRepository)
        assert result.name_with_owner == "octocat/Hello-World"
        assert result.name == "Hello-World"
        assert result.owner == "octocat"
        assert result.description == "This your first repo!"
        assert result.stargazer_count == 1420
        assert result.primary_language == "Python"
        assert "python" in result.repository_topics
        assert "web" in result.repository_topics
        assert "Python" in result.languages
        assert "JavaScript" in result.languages

    def test_parse_repository_data_minimal(self):
        """Test parsing repository data with minimal fields."""
        edge_data = {
            "node": {
                "id": "repo456",
                "nameWithOwner": "user/repo",
                "stargazerCount": 0,
                "url": "https://github.com/user/repo"
            }
        }
        
        result = _parse_repository_data(edge_data)
        
        assert result.name_with_owner == "user/repo"
        assert result.name == "repo"
        assert result.owner == "user"
        assert result.description is None
        assert result.primary_language is None
        assert result.repository_topics == []
        assert result.languages == []


class TestModels:
    """Test data models."""

    def test_starred_repositories_response_creation(self):
        """Test creating StarredRepositoriesResponse."""
        repo = StartedRepository(
            id="repo1",
            nameWithOwner="user/repo1",
            name="repo1",
            owner="user",
            stargazerCount=100,
            url="https://github.com/user/repo1"
        )
        
        response = StarredRepositoriesResponse(
            repositories=[repo],
            total_count=1,
            has_next_page=False,
            end_cursor=""
        )
        
        assert len(response.repositories) == 1
        assert response.total_count == 1
        assert response.has_next_page is False
        assert response.repositories[0].name_with_owner == "user/repo1"

    def test_repository_details_creation(self):
        """Test creating RepositoryDetails."""
        details = RepositoryDetails(
            readme_content="# Test Repository\nThis is a test."
        )
        
        assert "Test Repository" in details.readme_content
        assert "This is a test" in details.readme_content


class TestExceptions:
    """Test custom exceptions."""

    def test_github_api_error_creation(self):
        """Test creating GitHubAPIError."""
        error = GitHubAPIError("API Error")
        assert str(error) == "API Error"

    def test_rate_limit_error_creation(self):
        """Test creating RateLimitError."""
        error = RateLimitError("Rate limit exceeded")
        assert "Rate limit exceeded" in str(error)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_repository_name_parsing(self):
        """Test repository name parsing logic."""
        # Test the logic used in _parse_repository_data
        name_with_owner = "octocat/Hello-World"
        owner, name = name_with_owner.split("/", maxsplit=1)
        
        assert name == "Hello-World"
        assert owner == "octocat"

    def test_repository_name_parsing_complex(self):
        """Test repository name parsing with complex names."""
        name_with_owner = "microsoft/vscode-python"
        owner, name = name_with_owner.split("/", maxsplit=1)
        
        assert name == "vscode-python"
        assert owner == "microsoft"


class TestDataValidation:
    """Test data validation."""

    def test_started_repository_required_fields(self):
        """Test StartedRepository with required fields only."""
        repo = StartedRepository(
            id="repo1",
            nameWithOwner="user/repo1",
            name="repo1",
            owner="user",
            stargazerCount=100,
            url="https://github.com/user/repo1"
        )
        
        assert repo.repo_id == "repo1"
        assert repo.name_with_owner == "user/repo1"
        assert repo.stargazer_count == 100

    def test_repository_details_optional_fields(self):
        """Test RepositoryDetails with optional fields."""
        details = RepositoryDetails()
        
        assert details.readme_content is None