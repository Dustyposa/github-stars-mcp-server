"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError
from datetime import datetime

from github_stars_mcp.models import Repository, User, StarredRepository, PageInfo


class TestRepository:
    """Test cases for Repository model."""

    def test_repository_creation_with_all_fields(self, sample_repository_data):
        """Test Repository creation with all fields."""
        repo = Repository.model_validate(sample_repository_data)
        
        assert repo.name_with_owner == "octocat/Hello-World"
        assert repo.description == "This your first repo!"
        assert repo.stargazer_count == 1420
        assert repo.url == "https://github.com/octocat/Hello-World"
        assert repo.primary_language["name"] == "Python"
        assert repo.primary_language["color"] == "#3572A5"
        assert repo.is_private is False
        assert repo.is_fork is False
        assert repo.is_archived is False

    def test_repository_creation_with_minimal_fields(self):
        """Test Repository creation with minimal required fields."""
        minimal_data = {
            "nameWithOwner": "user/repo",
            "stargazerCount": 0,
            "url": "https://github.com/user/repo",
            "isPrivate": False,
            "isFork": False,
            "isArchived": False,
            "owner": {
                "login": "user",
                "avatarUrl": "https://github.com/user.png"
            }
        }
        
        repo = Repository.model_validate(minimal_data)
        
        assert repo.name_with_owner == "user/repo"
        assert repo.description is None
        assert repo.primary_language is None
        assert repo.created_at is None
        assert repo.updated_at is None
        assert repo.pushed_at is None

    def test_repository_field_aliases(self):
        """Test Repository field aliases work correctly."""
        data = {
            "nameWithOwner": "test/repo",
            "stargazerCount": 100,
            "url": "https://github.com/test/repo",
            "primaryLanguage": {"name": "JavaScript"},
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-02T00:00:00Z",
            "pushedAt": "2023-01-03T00:00:00Z",
            "isPrivate": True,
            "isFork": True,
            "isArchived": False,
            "owner": {
                "login": "test",
                "avatarUrl": "https://github.com/test.png"
            }
        }
        
        repo = Repository.model_validate(data)
        
        assert repo.name_with_owner == "test/repo"
        assert repo.stargazer_count == 100
        assert repo.primary_language["name"] == "JavaScript"
        assert repo.is_private is True
        assert repo.is_fork is True

    def test_repository_missing_required_fields(self):
        """Test Repository validation with missing required fields."""
        incomplete_data = {
            "nameWithOwner": "user/repo",
            # Missing stargazerCount, url, etc.
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Repository.model_validate(incomplete_data)
        
        error_fields = [error["loc"][0] for error in exc_info.value.errors()]
        assert "stargazer_count" in error_fields or "stargazerCount" in error_fields


class TestUser:
    """Test cases for User model."""

    def test_user_creation_with_all_fields(self, sample_user_data):
        """Test User creation with all fields."""
        user = User.model_validate(sample_user_data)
        
        assert user.login == "octocat"
        assert user.name == "The Octocat"
        assert user.bio == "A great octopus"
        assert user.avatar_url == "https://github.com/images/error/octocat_happy.gif"
        assert user.location == "San Francisco"
        assert user.company == "GitHub"
        assert user.email == "octocat@github.com"
        assert user.public_repos == 8
        assert user.followers == 3938
        assert user.following == 9

    def test_user_creation_with_minimal_fields(self):
        """Test User creation with minimal required fields."""
        minimal_data = {
            "login": "testuser",
            "avatarUrl": "https://github.com/testuser.png"
        }
        
        user = User.model_validate(minimal_data)
        
        assert user.login == "testuser"
        assert user.avatar_url == "https://github.com/testuser.png"
        assert user.name is None
        assert user.bio is None
        assert user.location is None
        assert user.company is None
        assert user.email is None

    def test_user_field_aliases(self):
        """Test User field aliases work correctly."""
        data = {
            "login": "testuser",
            "avatarUrl": "https://github.com/testuser.png",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-02T00:00:00Z",
            "publicRepos": 5
        }
        
        user = User.model_validate(data)
        
        assert user.avatar_url == "https://github.com/testuser.png"
        assert user.created_at.isoformat() == "2023-01-01T00:00:00+00:00"
        assert user.updated_at.isoformat() == "2023-01-02T00:00:00+00:00"
        assert user.public_repos == 5


class TestStarredRepository:
    """Test cases for StarredRepository model."""

    def test_starred_repository_creation(self):
        """Test StarredRepository creation."""
        data = {
            "starredAt": "2023-01-01T00:00:00Z",
            "repository": {
                "nameWithOwner": "user/repo",
                "stargazerCount": 100,
                "url": "https://github.com/user/repo",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False
            }
        }
        
        starred_repo = StarredRepository.model_validate(data)
        
        assert starred_repo.starred_at.isoformat() == "2023-01-01T00:00:00+00:00"
        assert starred_repo.repository.name_with_owner == "user/repo"
        assert starred_repo.repository.stargazer_count == 100

    def test_starred_repository_field_aliases(self):
        """Test StarredRepository field aliases work correctly."""
        data = {
            "starredAt": "2023-01-01T00:00:00Z",
            "repository": {
                "nameWithOwner": "test/repo",
                "stargazerCount": 50,
                "url": "https://github.com/test/repo",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False
            }
        }
        
        starred_repo = StarredRepository.model_validate(data)
        
        assert starred_repo.starred_at.isoformat() == "2023-01-01T00:00:00+00:00"
        assert starred_repo.repository.name_with_owner == "test/repo"


class TestPageInfo:
    """Test cases for PageInfo model."""

    def test_page_info_creation(self):
        """Test PageInfo creation."""
        data = {
            "endCursor": "cursor123",
            "hasNextPage": True,
            "hasPreviousPage": False,
            "startCursor": "cursor000"
        }
        
        page_info = PageInfo.model_validate(data)
        
        assert page_info.end_cursor == "cursor123"
        assert page_info.has_next_page is True
        assert page_info.has_previous_page is False
        assert page_info.start_cursor == "cursor000"

    def test_page_info_field_aliases(self):
        """Test PageInfo field aliases work correctly."""
        data = {
            "endCursor": "end123",
            "hasNextPage": False,
            "hasPreviousPage": True,
            "startCursor": "start456"
        }
        
        page_info = PageInfo.model_validate(data)
        
        assert page_info.end_cursor == "end123"
        assert page_info.has_next_page is False
        assert page_info.has_previous_page is True
        assert page_info.start_cursor == "start456"

    def test_page_info_minimal_fields(self):
        """Test PageInfo with minimal required fields."""
        data = {
            "hasNextPage": True,
            "hasPreviousPage": False
        }
        
        page_info = PageInfo.model_validate(data)
        
        assert page_info.has_next_page is True
        assert page_info.has_previous_page is False
        assert page_info.end_cursor is None
        assert page_info.start_cursor is None


class TestModelIntegration:
    """Integration tests for model interactions."""

    def test_repository_with_complex_owner(self):
        """Test Repository with complex owner data."""
        data = {
            "nameWithOwner": "complex/repo",
            "stargazerCount": 999,
            "url": "https://github.com/complex/repo",
            "isPrivate": False,
            "isFork": True,
            "isArchived": False,
            "owner": {
                "login": "complex",
                "avatarUrl": "https://github.com/complex.png",
                "name": "Complex Organization",
                "bio": "We build complex things",
                "location": "Everywhere",
                "company": "Complex Corp",
                "email": "contact@complex.org",
                "publicRepos": 42,
                "followers": 1000,
                "following": 100
            }
        }
        
        repo = Repository.model_validate(data)
        
        assert repo.name_with_owner == "complex/repo"
        assert repo.owner["login"] == "complex"
        assert repo.owner["name"] == "Complex Organization"
        assert repo.owner["publicRepos"] == 42

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