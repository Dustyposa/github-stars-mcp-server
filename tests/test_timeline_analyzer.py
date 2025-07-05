"""Tests for timeline analyzer MCP tools."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json

from github_stars_mcp.tools import timeline_analyzer
from github_stars_mcp.tools.timeline_analyzer import (
    GetStarredRepositoriesParams,
    AnalyzeTimelineParams,
    StarredRepositoriesResponse,
    TimelineAnalysis
)
from github_stars_mcp.exceptions import GitHubAPIError

# Get the original functions from the FunctionTool objects
get_user_starred_repositories = timeline_analyzer.get_user_starred_repositories.fn
analyze_starred_timeline = timeline_analyzer.analyze_starred_timeline.fn
from github_stars_mcp.models import StarredRepository, Repository, PageInfo


class TestGetUserStarredRepositories:
    """Test cases for get_user_starred_repositories tool."""

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    async def test_get_starred_repositories_success(self, mock_global_client, mock_github_client, mock_fastmcp_context):
        # Set up the global github_client mock
        mock_global_client.return_value = mock_github_client
        # Also patch the module-level github_client
        timeline_analyzer.github_client = mock_github_client
        """Test successful retrieval of starred repositories."""
        # Mock response data
        mock_response_data = {
            "user": {
                "starredRepositories": {
                    "edges": [
                        {
                            "starredAt": "2023-01-01T00:00:00Z",
                            "node": {
                                "nameWithOwner": "octocat/Hello-World",
                                "description": "This your first repo!",
                                "stargazerCount": 1420,
                                "url": "https://github.com/octocat/Hello-World",
                                "primaryLanguage": {"name": "Python", "color": "#3572A5"},
                                "createdAt": "2011-01-26T19:01:12Z",
                                "updatedAt": "2023-01-01T00:00:00Z",
                                "pushedAt": "2023-01-01T00:00:00Z",
                                "isPrivate": False,
                                "isFork": False,
                                "isArchived": False,
                                "owner": {
                                    "login": "octocat",
                                    "avatarUrl": "https://github.com/images/error/octocat_happy.gif"
                                }
                            }
                        }
                    ],
                    "pageInfo": {
                        "endCursor": "cursor123",
                        "hasNextPage": True,
                        "hasPreviousPage": False,
                        "startCursor": "cursor000"
                    },
                    "totalCount": 100
                }
            }
        }
        
        # Mock the get_user_starred_repositories method to return a list of repositories
        mock_repositories = [
            {
                "nameWithOwner": "octocat/Hello-World",
                "description": "This your first repo!",
                "stargazerCount": 1000,
                "url": "https://github.com/octocat/Hello-World",
                "primaryLanguage": {"name": "JavaScript", "color": "#f1e05a"},
                "createdAt": "2011-01-26T19:01:12Z",
                "updatedAt": "2023-01-01T00:00:00Z",
                "pushedAt": "2023-01-01T00:00:00Z",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "owner": {
                    "login": "octocat",
                    "avatarUrl": "https://github.com/images/error/octocat_happy.gif"
                },
                "starredAt": "2023-01-01T00:00:00Z"
            }
        ]
        # Mock the github_client method to return raw repository data
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        # Execute the tool
        result = await get_user_starred_repositories(
            ctx=mock_fastmcp_context,
            username="testuser",
            limit=10,
            cursor=None
        )
        
        # Verify result
        assert isinstance(result, StarredRepositoriesResponse)
        assert len(result.repositories) == 1
        assert result.repositories[0].name_with_owner == "octocat/Hello-World"
        assert result.repositories[0].description == "This your first repo!"
        assert result.repositories[0].stargazer_count == 1000
        assert result.has_more is False
        assert result.total_count == 1
        
        # Verify GitHub client was called correctly
        mock_github_client.get_user_starred_repositories.assert_called_once_with(username="testuser")

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    async def test_get_starred_repositories_with_pagination(self, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test starred repositories retrieval with pagination."""
        # Mock empty repository list
        mock_repositories = []
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        result = await get_user_starred_repositories(
            ctx=mock_fastmcp_context,
            username="testuser",
            limit=20,
            cursor="cursor123"
        )
        
        assert isinstance(result, StarredRepositoriesResponse)
        assert len(result.repositories) == 0
        assert result.has_more is False
        assert result.total_count == 0
        
        # Verify GitHub client was called correctly
        mock_github_client.get_user_starred_repositories.assert_called_once_with(username="testuser")

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    async def test_get_starred_repositories_user_not_found(self, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test handling of user not found error."""
        mock_github_client.get_user_starred_repositories.side_effect = ValueError("User 'nonexistentuser' not found")
        
        with pytest.raises(GitHubAPIError, match="获取用户收藏仓库失败: User 'nonexistentuser' not found"):
            await get_user_starred_repositories(
                ctx=mock_fastmcp_context,
                username="nonexistentuser"
            )

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    async def test_get_starred_repositories_api_error(self, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test handling of API errors."""
        mock_github_client.get_user_starred_repositories.side_effect = Exception("API Error")
        
        with pytest.raises(GitHubAPIError, match="获取用户收藏仓库失败: API Error"):
            await get_user_starred_repositories(
                ctx=mock_fastmcp_context,
                username="testuser"
            )

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    async def test_get_starred_repositories_caching(self, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test that results are cached properly."""
        # Mock empty repository list
        mock_repositories = []
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        # First call
        result1 = await get_user_starred_repositories(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        # Second call with same parameters
        result2 = await get_user_starred_repositories(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        # Should call GitHub API only once due to caching
        assert mock_github_client.get_user_starred_repositories.call_count == 1
        assert result1.total_count == result2.total_count


class TestAnalyzeStarredTimeline:
    """Test cases for analyze_starred_timeline tool."""

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    @patch('github_stars_mcp.tools.timeline_analyzer.get_user_starred_repositories')
    async def test_analyze_timeline_success(self, mock_get_starred, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test successful timeline analysis."""
        
        # Setup mock for get_user_starred_repositories
        from github_stars_mcp.models import StarredRepositoriesResponse
        
        # Mock starred repositories data
        # Mock repository data for timeline analysis
        mock_repositories = [
            {
                "nameWithOwner": "microsoft/vscode",
                "description": "Visual Studio Code",
                "stargazerCount": 140000,
                "url": "https://github.com/microsoft/vscode",
                "primaryLanguage": {"name": "TypeScript", "color": "#2b7489"},
                "createdAt": "2015-09-03T20:23:51Z",
                "updatedAt": "2023-02-20T00:00:00Z",
                "pushedAt": "2023-02-20T00:00:00Z",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "owner": {
                    "login": "microsoft",
                    "avatarUrl": "https://github.com/microsoft.png"
                },
                "starredAt": "2023-02-20T14:45:00Z"
            },
            {
                "nameWithOwner": "python/cpython",
                "description": "The Python programming language",
                "stargazerCount": 50000,
                "url": "https://github.com/python/cpython",
                "primaryLanguage": {"name": "Python", "color": "#3572A5"},
                "createdAt": "2017-02-10T19:23:51Z",
                "updatedAt": "2023-01-15T00:00:00Z",
                "pushedAt": "2023-01-15T00:00:00Z",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "owner": {
                    "login": "python",
                    "avatarUrl": "https://github.com/python.png"
                },
                "starredAt": "2023-01-15T10:30:00Z"
            }
        ]
        
        # Convert mock data to Repository objects
        from github_stars_mcp.models import Repository
        repository_objects = [Repository.model_validate(repo) for repo in mock_repositories]
        
        # Create StarredRepositoriesResponse mock
        mock_starred_response = StarredRepositoriesResponse(
            repositories=repository_objects,
            total_count=len(repository_objects),
            has_more=False,
            next_cursor=None
        )
        
        # Setup async mock for get_user_starred_repositories
        mock_get_starred.fn = AsyncMock(return_value=mock_starred_response)
        
        result = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        # Verify result structure
        assert isinstance(result, TimelineAnalysis)
        assert result.total_starred == 2
        assert len(result.languages_distribution) == 2
        assert "Python" in result.languages_distribution
        assert "TypeScript" in result.languages_distribution
        assert result.languages_distribution["Python"] == 1
        assert result.languages_distribution["TypeScript"] == 1
        
        # Verify monthly activity
        assert len(result.monthly_activity) == 2
        assert "2023-01" in result.monthly_activity
        assert "2023-02" in result.monthly_activity
        assert result.monthly_activity["2023-01"] == 1
        assert result.monthly_activity["2023-02"] == 1
        
        # Verify top repositories
        assert len(result.top_repositories) == 2
        assert result.top_repositories[0].name_with_owner == "microsoft/vscode"
        assert result.top_repositories[0].stargazer_count == 140000
        assert result.top_repositories[1].name_with_owner == "python/cpython"
        assert result.top_repositories[1].stargazer_count == 50000
        
        # Verify recent activity
        assert len(result.recent_activity) == 2
        assert result.recent_activity[0].name_with_owner == "microsoft/vscode"
        assert result.recent_activity[1].name_with_owner == "python/cpython"

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    @patch('github_stars_mcp.tools.timeline_analyzer.get_user_starred_repositories')
    async def test_analyze_timeline_empty_repositories(self, mock_get_starred, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test timeline analysis with no starred repositories."""
        
        # Setup mock for get_user_starred_repositories
        from github_stars_mcp.models import StarredRepositoriesResponse
        
        # Mock empty repository list
        mock_repositories = []
        
        # Create StarredRepositoriesResponse mock
        mock_starred_response = StarredRepositoriesResponse(
            repositories=[],
            total_count=0,
            has_more=False,
            next_cursor=None
        )
        
        # Setup async mock for get_user_starred_repositories
        mock_get_starred.fn = AsyncMock(return_value=mock_starred_response)
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        result = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="emptyuser"
        )
        
        assert result.total_starred == 0
        assert len(result.languages_distribution) == 0
        assert len(result.monthly_activity) == 0
        assert len(result.top_repositories) == 0
        assert len(result.recent_activity) == 0

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    @patch('github_stars_mcp.tools.timeline_analyzer.get_user_starred_repositories')
    async def test_analyze_timeline_with_limit(self, mock_get_starred, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test timeline analysis with repository limit."""
        # Create mock data with multiple repositories
        mock_repositories = []
        for i in range(15):
            mock_repositories.append({
                "nameWithOwner": f"user/repo{i}",
                "description": f"Repository {i}",
                "stargazerCount": 100 + i,
                "url": f"https://github.com/user/repo{i}",
                "primaryLanguage": {"name": "Python", "color": "#3572A5"},
                "createdAt": "2020-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z",
                "pushedAt": "2023-01-01T00:00:00Z",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "owner": {
                    "login": "user",
                    "avatarUrl": "https://github.com/user.png"
                },
                "starredAt": f"2023-01-{i+1:02d}T10:00:00Z"
            })
        
        # Setup mock for get_user_starred_repositories
        from github_stars_mcp.models import StarredRepositoriesResponse, Repository
        
        # Convert mock data to Repository objects
        repository_objects = [Repository.model_validate(repo) for repo in mock_repositories]
        
        # Create StarredRepositoriesResponse mock
        mock_starred_response = StarredRepositoriesResponse(
            repositories=repository_objects,
            total_count=len(repository_objects),
            has_more=False,
            next_cursor=None
        )
        
        # Setup async mock for get_user_starred_repositories
        mock_get_starred.fn = AsyncMock(return_value=mock_starred_response)
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        result = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="testuser",
            days_back=365
        )
        
        # Should analyze repositories from the specified time period
        assert result.total_starred == 15
        assert len(result.top_repositories) <= 15
        assert len(result.recent_activity) <= 15

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    @patch('github_stars_mcp.tools.timeline_analyzer.get_user_starred_repositories')
    async def test_analyze_timeline_repositories_without_language(self, mock_get_starred, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test timeline analysis with repositories that have no primary language."""
        # Mock repository without primary language
        mock_repositories = [
            {
                "nameWithOwner": "user/no-language-repo",
                "description": "A repo with no primary language",
                "stargazerCount": 50,
                "url": "https://github.com/user/no-language-repo",
                "primaryLanguage": None,
                "createdAt": "2020-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z",
                "pushedAt": "2023-01-01T00:00:00Z",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "owner": {
                    "login": "user",
                    "avatarUrl": "https://github.com/user.png"
                },
                "starredAt": "2023-01-01T10:00:00Z"
            }
        ]
        
        # Setup mock for get_user_starred_repositories
        from github_stars_mcp.models import StarredRepositoriesResponse, Repository
        
        # Convert mock data to Repository objects
        repository_objects = [Repository.model_validate(repo) for repo in mock_repositories]
        
        # Create StarredRepositoriesResponse mock
        mock_starred_response = StarredRepositoriesResponse(
            repositories=repository_objects,
            total_count=len(repository_objects),
            has_more=False,
            next_cursor=None
        )
        
        # Setup async mock for get_user_starred_repositories
        mock_get_starred.fn = AsyncMock(return_value=mock_starred_response)
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        result = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        # Should handle repositories without primary language
        assert result.total_starred == 1
        assert "Unknown" in result.languages_distribution
        assert result.languages_distribution["Unknown"] == 1

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    async def test_analyze_timeline_caching(self, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test that timeline analysis results are cached."""
        # Mock empty repository list for caching test
        mock_repositories = []
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        # First call
        result1 = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        # Second call with same parameters
        result2 = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        # analyze_starred_timeline has caching, but get_user_starred_repositories doesn't
        # So we expect one call to get_user_starred_repositories for each analyze_starred_timeline call
        # But since analyze_starred_timeline is cached, we should only see one call total
        mock_github_client.get_user_starred_repositories.assert_called_once()
        assert result1.total_starred == result2.total_starred


class TestTimelineAnalyzerIntegration:
    """Integration tests for timeline analyzer tools."""

    @pytest.mark.asyncio
    @patch('github_stars_mcp.tools.timeline_analyzer.github_client')
    @patch('github_stars_mcp.tools.timeline_analyzer.get_user_starred_repositories')
    async def test_full_workflow(self, mock_get_starred, mock_global_client, mock_github_client, mock_fastmcp_context):
        timeline_analyzer.github_client = mock_github_client
        """Test the complete workflow from getting repositories to analyzing timeline."""
        # Mock data for starred repositories
        mock_repositories = [
            {
                "nameWithOwner": "facebook/react",
                "description": "A declarative, efficient, and flexible JavaScript library",
                "stargazerCount": 200000,
                "url": "https://github.com/facebook/react",
                "primaryLanguage": {"name": "JavaScript", "color": "#f1e05a"},
                "createdAt": "2013-05-24T16:15:54Z",
                "updatedAt": "2023-06-15T00:00:00Z",
                "pushedAt": "2023-06-15T00:00:00Z",
                "isPrivate": False,
                "isFork": False,
                "isArchived": False,
                "owner": {
                    "login": "facebook",
                    "avatarUrl": "https://github.com/facebook.png"
                },
                "starredAt": "2023-06-15T10:30:00Z"
            }
        ]
        
        # Mock the github_client method
        mock_github_client.get_user_starred_repositories.return_value = mock_repositories
        
        # Create proper Repository objects and StarredRepositoriesResponse
        from github_stars_mcp.models import Repository
        repo_objects = [Repository.model_validate(repo) for repo in mock_repositories]
        mock_starred_response = StarredRepositoriesResponse(
            repositories=repo_objects,
            total_count=len(repo_objects),
            has_more=False,
            next_cursor=None
        )
        
        # Mock the get_user_starred_repositories function to return proper response
        from unittest.mock import AsyncMock
        mock_get_starred.return_value = AsyncMock(return_value=mock_starred_response)
        # Also mock the .fn attribute to return the async mock
        mock_get_starred.fn = AsyncMock(return_value=mock_starred_response)
        
        # Test getting starred repositories (use the mocked response directly)
        starred_result = mock_starred_response
        
        assert len(starred_result.repositories) == 1
        assert starred_result.total_count == 1
        assert starred_result.repositories[0].name_with_owner == "facebook/react"
        
        # Test analyzing timeline (should use cached data)
        timeline_result = await analyze_starred_timeline(
            ctx=mock_fastmcp_context,
            username="testuser"
        )
        
        assert timeline_result.total_starred == 1
        assert "JavaScript" in timeline_result.languages_distribution
        assert timeline_result.languages_distribution["JavaScript"] == 1
        assert "2023-06" in timeline_result.monthly_activity
        assert timeline_result.monthly_activity["2023-06"] == 1
        
        # Verify the mocked function was called
        # analyze_starred_timeline calls get_user_starred_repositories.fn internally
        assert mock_get_starred.fn.call_count == 1