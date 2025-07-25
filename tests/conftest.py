"""Pytest configuration and fixtures for GitHub Stars MCP Server tests."""

import asyncio
import os
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx
from fastmcp import Context

from github_stars_mcp.config import Settings
from github_stars_mcp.utils.github_client import GitHubClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with mock values."""
    return Settings(
        github_token="test_token_123",
        cache_dir=".test_cache",
        log_level="DEBUG"
    )


@pytest.fixture
def mock_context() -> Context:
    """Create a mock FastMCP context for testing."""
    context = MagicMock(spec=Context)
    context.info = MagicMock()
    context.warning = MagicMock()
    context.error = MagicMock()
    context.debug = MagicMock()
    return context


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """Create a mock httpx AsyncClient for testing."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
async def github_client(test_settings: Settings, mock_httpx_client: AsyncMock) -> GitHubClient:
    """Create a GitHub client instance for testing."""
    client = GitHubClient(settings=test_settings)
    # Replace the real httpx client with our mock
    client._client = mock_httpx_client
    return client


@pytest.fixture
def sample_repository_data() -> Dict[str, Any]:
    """Sample repository data for testing."""
    return {
        "nameWithOwner": "octocat/Hello-World",
        "name": "Hello-World",
        "owner": "octocat",
        "description": "This your first repo!",
        "stargazerCount": 1420,
        "url": "https://github.com/octocat/Hello-World",
        "primaryLanguage": "Python",
        "createdAt": "2011-01-26T19:01:12Z",
        "updatedAt": "2011-01-26T19:14:43Z",
        "pushedAt": "2011-01-26T19:06:43Z",
        "isPrivate": False,
        "isFork": False,
        "isArchived": False
    }


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    return {
        "login": "octocat",
        "name": "The Octocat",
        "bio": "A great octopus",
        "avatarUrl": "https://github.com/images/error/octocat_happy.gif",
        "location": "San Francisco",
        "company": "GitHub",
        "email": "octocat@github.com",
        "createdAt": "2011-01-25T18:44:36Z",
        "updatedAt": "2017-11-01T21:56:45Z",
        "publicRepos": 8,
        "followers": 3938,
        "following": 9
    }


@pytest.fixture
def sample_starred_repositories_response() -> Dict[str, Any]:
    """Sample starred repositories GraphQL response for testing."""
    return {
        "data": {
            "user": {
                "starredRepositories": {
                    "pageInfo": {
                        "endCursor": "Y3Vyc29yOnYyOpK5MjAxOS0wNy0wOVQxNDozMDowMSswODowMM4AEqgB",
                        "hasNextPage": True
                    },
                    "nodes": [
                        {
                            "nameWithOwner": "microsoft/vscode",
                            "description": "Visual Studio Code",
                            "stargazerCount": 162000,
                            "url": "https://github.com/microsoft/vscode",
                            "primaryLanguage": {
                                "name": "TypeScript",
                                "color": "#2b7489"
                            }
                        },
                        {
                            "nameWithOwner": "python/cpython",
                            "description": "The Python programming language",
                            "stargazerCount": 62000,
                            "url": "https://github.com/python/cpython",
                            "primaryLanguage": {
                                "name": "Python",
                                "color": "#3572A5"
                            }
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def mock_httpx_response(sample_starred_repositories_response: Dict[str, Any]) -> MagicMock:
    """Create a mock httpx response for testing."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = sample_starred_repositories_response
    response.raise_for_status.return_value = None
    return response


@pytest.fixture
def mock_github_client() -> AsyncMock:
    """Create a mock GitHub client for testing."""
    client = AsyncMock()
    client.execute_query = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def mock_fastmcp_context() -> MagicMock:
    """Create a mock FastMCP context for testing."""
    context = MagicMock()
    context.info = MagicMock()
    context.warning = MagicMock()
    context.error = MagicMock()
    context.debug = MagicMock()
    return context


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")
    monkeypatch.setenv("CACHE_DIR", ".test_cache")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")