"""Tests for MCP tools functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from github_stars_mcp.models import (
    StarredRepositoriesResponse,
    StartedRepository,
    BatchRepositoryDetailsResponse,
    RepositoryDetails
)
from github_stars_mcp.tools.starred_repo_list import _get_user_starred_repositories_impl
from github_stars_mcp.tools.batch_repo_details import fetch_single_repository_details, fetch_multi_repository_details
from github_stars_mcp.exceptions import GitHubAPIError, RateLimitError


class TestStarredRepoList:
    """Test starred repository list functionality."""

    @pytest.mark.asyncio
    async def test_get_starred_repositories_success(self, mock_context):
        """Test successful retrieval of starred repositories."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client') as mock_ensure, \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_ensure.return_value = AsyncMock()
            mock_request.return_value = AsyncMock()
            
            mock_validate.return_value = "testuser"
            mock_request.return_value = {
                "edges": [
                    {
                        "node": {
                            "id": "repo1",
                            "nameWithOwner": "user/repo1",
                            "stargazerCount": 100,
                            "url": "https://github.com/user/repo1"
                        }
                    }
                ],
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            result = await _get_user_starred_repositories_impl(mock_context, "testuser")
            
            assert isinstance(result, StarredRepositoriesResponse)
            assert len(result.repositories) == 1
            assert result.repositories[0].nameWithOwner == "user/repo1"
            assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_empty_username_handling(self, mock_context):
        """Test handling of empty username."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request:
            
            mock_request.return_value = {
                "edges": [],
                "totalCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            result = await _get_user_starred_repositories_impl(mock_context, "")
            
            assert isinstance(result, StarredRepositoriesResponse)
            assert result.total_count == 0


class TestBatchRepoDetails:
    """Test batch repository details functionality."""

    @pytest.mark.asyncio
    async def test_fetch_single_repository_details_success(self, mock_context):
        """Test successful fetch of single repository details."""
        mock_github_client = AsyncMock()
        mock_github_client.get_repository_readme.return_value = {
            "content": "# Test Repository\nThis is a test."
        }
        semaphore = AsyncMock()
        
        result = await fetch_single_repository_details(
            mock_context, "user/repo", mock_github_client, semaphore
        )
        
        assert isinstance(result, RepositoryDetails)
        assert "Test Repository" in result.readme_content

    @pytest.mark.asyncio
    async def test_fetch_single_repository_details_failure(self, mock_context):
        """Test fetch single repository details with failure."""
        mock_github_client = AsyncMock()
        mock_github_client.get_repository_readme.side_effect = Exception("API Error")
        semaphore = AsyncMock()
        
        result = await fetch_single_repository_details(
            mock_context, "nonexistent/repo", mock_github_client, semaphore
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_multi_repository_details_success(self, mock_context):
        """Test successful fetch of multiple repository details."""
        mock_github_client = AsyncMock()
        mock_github_client.get_multi_repository_readme.return_value = {
            "user/repo1": RepositoryDetails(readme_content="# Repo 1"),
            "user/repo2": RepositoryDetails(readme_content="# Repo 2")
        }
        
        repo_ids = ["user/repo1", "user/repo2"]
        result = await fetch_multi_repository_details(mock_context, repo_ids, mock_github_client)
        
        assert isinstance(result, BatchRepositoryDetailsResponse)
        assert len(result.data) == 2
        assert "user/repo1" in result.data
        assert "user/repo2" in result.data


class TestErrorHandling:
    """Test error handling across tools."""

    @pytest.mark.asyncio
    async def test_github_api_error_handling(self, mock_context):
        """Test handling of GitHub API errors."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client') as mock_ensure:
            mock_ensure.side_effect = GitHubAPIError("API Error")
            
            with pytest.raises(GitHubAPIError):
                await _get_user_starred_repositories_impl(mock_context, "testuser")

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, mock_context):
        """Test handling of rate limit errors."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client') as mock_ensure:
            mock_ensure.side_effect = RateLimitError("Rate limit exceeded")
            
            with pytest.raises(RateLimitError) as exc_info:
                await _get_user_starred_repositories_impl(mock_context, "testuser")
            
            assert "Rate limit exceeded" in str(exc_info.value)
            # RateLimitError doesn't have retry_after attribute in this implementation


class TestDataParsing:
    """Test data parsing functionality."""

    @pytest.mark.asyncio
    async def test_repository_data_parsing(self, mock_context):
        """Test parsing of repository data from GitHub API."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_validate.return_value = "testuser"
            mock_request.return_value = {
                "edges": [
                    {
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
                        },
                        "starredAt": "2023-01-01T00:00:00Z"
                    }
                ],
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            result = await _get_user_starred_repositories_impl(mock_context, "testuser")
            
            assert len(result.repositories) == 1
            repo = result.repositories[0]
            assert repo.nameWithOwner == "octocat/Hello-World"
            assert repo.name == "Hello-World"
            assert repo.owner == "octocat"
            assert repo.description == "This your first repo!"
            assert repo.stargazerCount == 1420
            assert repo.primaryLanguage == "Python"
            assert "python" in repo.repositoryTopics
            assert "web" in repo.repositoryTopics
            assert "Python" in repo.languages
            assert "JavaScript" in repo.languages


class TestPagination:
    """Test pagination functionality."""

    @pytest.mark.asyncio
    async def test_pagination_handling(self, mock_context):
        """Test handling of paginated responses."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_validate.return_value = "testuser"
            mock_request.return_value = {
                "edges": [
                    {
                        "node": {
                            "id": f"repo{i}",
                            "nameWithOwner": f"user/repo{i}",
                            "stargazerCount": 100 + i,
                            "url": f"https://github.com/user/repo{i}"
                        }
                    } for i in range(50)
                ],
                "totalCount": 100,
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor50"}
            }
            
            result = await _get_user_starred_repositories_impl(mock_context, "testuser")
            
            assert len(result.repositories) == 50
            assert result.total_count == 100
            assert result.has_next_page is True
            assert result.end_cursor == "cursor50"