"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError
from datetime import datetime

from github_stars_mcp.models import StartedRepository, StarredRepositoriesResponse


class TestStartedRepository:
    """Test cases for StartedRepository model."""

    def test_repository_creation_with_all_fields(self):
        """Test creating a repository with all fields."""
        repo_data = {
            "id": "repo123",
            "nameWithOwner": "owner/repo",
            "name": "repo",
            "owner": "owner",
            "description": "A test repository",
            "stargazerCount": 100,
            "url": "https://github.com/owner/repo",
            "primaryLanguage": "Python",
            "starredAt": "2023-01-01T00:00:00Z",
            "pushedAt": "2023-01-02T00:00:00Z",
            "diskUsage": 1024,
            "repositoryTopics": ["python", "web"],
            "languages": ["Python", "JavaScript"]
        }
        
        repo = StartedRepository.model_validate(repo_data)
        
        assert repo.repo_id == "repo123"
        assert repo.name_with_owner == "owner/repo"
        assert repo.name == "repo"
        assert repo.owner == "owner"
        assert repo.description == "A test repository"
        assert repo.stargazer_count == 100
        assert repo.url == "https://github.com/owner/repo"
        assert repo.primary_language == "Python"
        assert repo.disk_usage == 1024
        assert repo.repository_topics == ["python", "web"]
        assert repo.languages == ["Python", "JavaScript"]

    def test_repository_creation_with_minimal_fields(self):
        """Test creating a repository with minimal required fields."""
        repo_data = {
            "id": "repo123",
            "nameWithOwner": "owner/repo",
            "name": "repo",
            "owner": "owner",
            "stargazerCount": 0,
            "url": "https://github.com/owner/repo"
        }
        
        repo = StartedRepository(**repo_data)
        
        assert repo.repo_id == "repo123"
        assert repo.name_with_owner == "owner/repo"
        assert repo.name == "repo"
        assert repo.owner == "owner"
        assert repo.description is None
        assert repo.stargazer_count == 0
        assert repo.url == "https://github.com/owner/repo"
        assert repo.primary_language is None
        assert repo.starred_at is None
        assert repo.pushed_at is None
        assert repo.disk_usage is None
        assert repo.repository_topics == []
        assert repo.languages == []

    def test_repository_field_aliases(self):
        """Test that field aliases work correctly."""
        repo_data = {
            "id": "repo123",
            "nameWithOwner": "owner/repo",
            "name": "repo",
            "owner": "owner",
            "stargazerCount": 50,
            "url": "https://github.com/owner/repo",
            "primaryLanguage": "JavaScript",
            "starredAt": "2023-01-01T00:00:00Z",
            "pushedAt": "2023-01-02T00:00:00Z",
            "diskUsage": 2048,
            "repositoryTopics": ["js", "frontend"]
        }
        
        repo = StartedRepository(**repo_data)
        
        # Test that aliases map to correct internal field names
        assert repo.repo_id == "repo123"  # id -> repo_id
        assert repo.name_with_owner == "owner/repo"  # nameWithOwner -> name_with_owner
        assert repo.stargazer_count == 50  # stargazerCount -> stargazer_count
        assert repo.primary_language == "JavaScript"  # primaryLanguage -> primary_language
        assert repo.disk_usage == 2048  # diskUsage -> disk_usage
        assert repo.repository_topics == ["js", "frontend"]  # repositoryTopics -> repository_topics

    def test_repository_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError):
            StartedRepository()
        
        with pytest.raises(ValidationError):
            StartedRepository(id="repo123")  # Missing other required fields



class TestStarredRepositoriesResponse:
    """Test cases for StarredRepositoriesResponse model."""

    def test_starred_repositories_response_creation(self):
        """Test StarredRepositoriesResponse creation."""
        data = {
            "repositories": [],
            "total_count": 0,
            "has_next_page": False,
            "end_cursor": None
        }
        
        response = StarredRepositoriesResponse.model_validate(data)
        
        assert response.repositories == []
        assert response.total_count == 0
        assert response.has_next_page is False
        assert response.end_cursor is None

    def test_starred_repositories_response_with_data(self):
        """Test StarredRepositoriesResponse with repository data."""
        repo_data = {
            "id": "repo123",
            "nameWithOwner": "test/repo",
            "name": "repo",
            "owner": "test",
            "stargazerCount": 50,
            "url": "https://github.com/test/repo"
        }
        
        data = {
            "repositories": [repo_data],
            "total_count": 1,
            "has_next_page": True,
            "end_cursor": "cursor123"
        }
        
        response = StarredRepositoriesResponse.model_validate(data)
        
        assert len(response.repositories) == 1
        assert response.repositories[0].name == "repo"
        assert response.total_count == 1
        assert response.has_next_page is True
        assert response.end_cursor == "cursor123"



class TestModelIntegration:
    """Integration tests for model interactions."""

    def test_repository_serialization_roundtrip(self):
        """Test that repository can be serialized and deserialized."""
        repo_data = {
            "id": "repo123",
            "nameWithOwner": "owner/repo",
            "name": "repo",
            "owner": "owner",
            "description": "A test repository",
            "stargazerCount": 100,
            "url": "https://github.com/owner/repo",
            "primaryLanguage": "Python",
            "repositoryTopics": ["python", "web"],
            "languages": ["Python", "JavaScript"]
        }
        
        # Create repository
        repo = StartedRepository(**repo_data)
        
        # Serialize to dict
        serialized = repo.model_dump(by_alias=True)
        
        # Deserialize back
        repo_restored = StartedRepository(**serialized)
        
        # Should be identical
        assert repo == repo_restored