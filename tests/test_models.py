"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError
from datetime import datetime

from github_stars_mcp.models import Repository, StarredRepository


class TestRepository:
    """Test cases for Repository model."""

    def test_repository_creation_with_all_fields(self, sample_repository_data):
        """Test Repository creation with all fields."""
        repo = Repository.model_validate(sample_repository_data)
        
        assert repo.name_with_owner == "octocat/Hello-World"
        assert repo.name == "Hello-World"
        assert repo.owner == "octocat"
        assert repo.description == "This your first repo!"
        assert repo.stargazer_count == 1420
        assert repo.url == "https://github.com/octocat/Hello-World"
        assert repo.primary_language == "Python"
        assert repo.is_private is False
        assert repo.is_fork is False
        assert repo.is_archived is False

    def test_repository_creation_with_minimal_fields(self):
        """Test Repository creation with minimal required fields."""
        minimal_data = {
            "nameWithOwner": "user/repo",
            "name": "repo",
            "owner": "user",
            "stargazerCount": 0,
            "url": "https://github.com/user/repo"
        }
        
        repo = Repository.model_validate(minimal_data)
        
        assert repo.name_with_owner == "user/repo"
        assert repo.name == "repo"
        assert repo.owner == "user"
        assert repo.description is None
        assert repo.primary_language is None
        assert repo.pushed_at is None

    def test_repository_field_aliases(self):
        """Test Repository field aliases work correctly."""
        data = {
            "nameWithOwner": "test/repo",
            "name": "repo",
            "owner": "test",
            "stargazerCount": 100,
            "url": "https://github.com/test/repo",
            "primaryLanguage": "JavaScript",
            "pushedAt": "2023-01-03T00:00:00Z",
            "isPrivate": True,
            "isFork": True,
            "isArchived": False
        }
        
        repo = Repository.model_validate(data)
        
        assert repo.name_with_owner == "test/repo"
        assert repo.name == "repo"
        assert repo.owner == "test"
        assert repo.stargazer_count == 100
        assert repo.primary_language == "JavaScript"
        assert repo.is_private is True
        assert repo.is_fork is True

    def test_repository_missing_required_fields(self):
        """Test Repository validation with missing required fields."""
        incomplete_data = {
            "nameWithOwner": "user/repo",
            # Missing name, owner, stargazerCount, url, etc.
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Repository.model_validate(incomplete_data)
        
        error_fields = [error["loc"][0] for error in exc_info.value.errors()]
        required_fields = ["name", "owner", "stargazer_count", "url"]
        assert any(field in error_fields for field in required_fields)



class TestStarredRepository:
    """Test cases for StarredRepository model."""

    def test_starred_repository_creation(self):
        """Test StarredRepository creation."""
        data = {
            "id": "repo123",
            "name": "repo",
            "full_name": "user/repo",
            "url": "https://github.com/user/repo",
            "stars_count": 100,
            "forks_count": 10,
            "topics": [],
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "starred_at": "2023-01-01T00:00:00Z",
            "is_fork": False,
            "is_private": False,
            "is_archived": False
        }
        
        starred_repo = StarredRepository.model_validate(data)
        
        assert starred_repo.starred_at.isoformat() == "2023-01-01T00:00:00+00:00"
        assert starred_repo.full_name == "user/repo"
        assert starred_repo.stars_count == 100

    def test_starred_repository_field_aliases(self):
        """Test StarredRepository field aliases work correctly."""
        data = {
            "id": "repo456",
            "name": "repo",
            "full_name": "test/repo",
            "url": "https://github.com/test/repo",
            "stars_count": 50,
            "forks_count": 5,
            "topics": [],
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "starred_at": "2023-01-01T00:00:00Z",
            "is_fork": False,
            "is_private": False,
            "is_archived": False
        }
        
        starred_repo = StarredRepository.model_validate(data)
        
        assert starred_repo.starred_at.isoformat() == "2023-01-01T00:00:00+00:00"
        assert starred_repo.full_name == "test/repo"



class TestModelIntegration:
    """Integration tests for model interactions."""

    def test_repository_with_complex_owner(self):
        """Test Repository with complex owner data."""
        data = {
            "nameWithOwner": "complex/repo",
            "name": "repo",
            "owner": "complex",
            "stargazerCount": 999,
            "url": "https://github.com/complex/repo",
            "isPrivate": False,
            "isFork": True,
            "isArchived": False
        }
        
        repo = Repository.model_validate(data)
        
        assert repo.name_with_owner == "complex/repo"
        assert repo.owner == "complex"
        assert repo.name == "repo"
        assert repo.is_fork is True

    def test_model_serialization_roundtrip(self, sample_repository_data):
        """Test that models can be serialized and deserialized correctly."""
        # Create model from data
        original_repo = Repository.model_validate(sample_repository_data)
        
        # Serialize to dict
        serialized = original_repo.model_dump(by_alias=True)
        
        # Deserialize back to model
        restored_repo = Repository.model_validate(serialized)
        
        # Should be identical
        assert original_repo.name_with_owner == restored_repo.name_with_owner
        assert original_repo.stargazer_count == restored_repo.stargazer_count
        assert original_repo.url == restored_repo.url
        assert original_repo.primary_language == restored_repo.primary_language