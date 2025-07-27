"""Tests for GitHub GraphQL client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timedelta

from github_stars_mcp.utils.github_client import GitHubClient
from github_stars_mcp.config import Settings
from github_stars_mcp.exceptions import GitHubAPIError


class TestGitHubClient:
    """Test cases for GitHubClient."""

    @pytest.fixture
    def client_settings(self):
        """Create test settings for GitHub client."""
        return Settings(
            github_token="test_token_123"
        )

    @pytest.fixture
    def github_client(self, client_settings):
        """Create GitHub client instance for testing."""
        return GitHubClient(client_settings.github_token)

    def test_client_initialization(self, github_client, client_settings):
        """Test GitHub client initialization."""
        assert github_client.token == client_settings.github_token
        assert github_client.base_url == "https://api.github.com/graphql"
        assert "Bearer" in github_client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_execute_query_success(self, github_client):
        """Test successful GraphQL query execution."""
        # Mock response data
        mock_response_data = {
            "data": {
                "user": {
                    "login": "testuser",
                    "name": "Test User"
                }
            }
        }
        
        # Mock httpx client
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { user(login: $username) { login name } }"
            variables = {"username": "testuser"}
            
            result = await github_client.query(query, variables)
            
            assert result == mock_response_data["data"]
            
            # Verify the request was made correctly
            mock_client.post.assert_called_once_with(
                github_client.base_url,
                json={
                    "query": query,
                    "variables": variables
                },
                headers=github_client.headers
            )

    @pytest.mark.asyncio
    async def test_execute_query_with_errors(self, github_client):
        """Test GraphQL query execution with GraphQL errors."""
        mock_response_data = {
            "data": None,
            "errors": [
                {
                    "message": "Could not resolve to a User with the login of 'nonexistent'.",
                    "type": "NOT_FOUND",
                    "path": ["user"]
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { user(login: $username) { login } }"
            variables = {"username": "nonexistent"}
            
            with pytest.raises(Exception, match="GraphQL errors"):
                await github_client.query(query, variables)

    @pytest.mark.asyncio
    async def test_execute_query_http_error(self, github_client):
        """Test GraphQL query execution with HTTP errors."""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { viewer { login } }"
            
            with pytest.raises(Exception, match="Invalid GitHub token"):
                await github_client.query(query)

    @pytest.mark.asyncio
    async def test_execute_query_network_error(self, github_client):
        """Test GraphQL query execution with network errors."""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            
            query = "query { viewer { login } }"
            
            with pytest.raises(GitHubAPIError, match="Request failed"):
                await github_client.query(query)

    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, github_client):
        """Test GraphQL query execution with timeout."""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            
            query = "query { viewer { login } }"
            
            with pytest.raises(Exception, match="Request timeout"):
                await github_client.query(query)

    @pytest.mark.asyncio
    async def test_execute_query_rate_limit(self, github_client):
        """Test GraphQL query execution with rate limiting."""
        # Mock rate limit response
        mock_response_data = {
            "data": {
                "rateLimit": {
                    "limit": 5000,
                    "cost": 1,
                    "remaining": 0,
                    "resetAt": (datetime.now() + timedelta(hours=1)).isoformat()
                }
            },
            "errors": [
                {
                    "type": "RATE_LIMITED",
                    "message": "API rate limit exceeded"
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { viewer { login } }"
            
            with pytest.raises(Exception, match="GraphQL errors"):
                await github_client.query(query)

    @pytest.mark.asyncio
    async def test_execute_query_partial_data_with_errors(self, github_client):
        """Test GraphQL query execution with partial data and errors."""
        mock_response_data = {
            "data": {
                "user": {
                    "login": "testuser",
                    "name": None  # This field failed
                }
            },
            "errors": [
                {
                    "message": "Field 'name' is not accessible",
                    "path": ["user", "name"]
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { user(login: $username) { login name } }"
            variables = {"username": "testuser"}
            
            # Should raise exception even with partial data when errors exist
            with pytest.raises(Exception, match="GraphQL errors"):
                await github_client.query(query, variables)

    @pytest.mark.asyncio
    async def test_execute_query_empty_response(self, github_client):
        """Test GraphQL query execution with empty response."""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { viewer { login } }"
            
            result = await github_client.query(query)
            
            # Should return empty dict for empty data
            assert result == {}

    @pytest.mark.asyncio
    async def test_execute_query_malformed_json(self, github_client):
        """Test GraphQL query execution with malformed JSON response."""
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = "query { viewer { login } }"
            
            with pytest.raises(ValueError, match="Invalid JSON"):
                await github_client.query(query)

    # Context manager test removed - GitHubClient doesn't implement async context manager protocol

    # Close method test removed - GitHubClient doesn't have a close method

    def test_headers_configuration(self, client_settings):
        """Test that headers are configured correctly."""
        client = GitHubClient(client_settings.github_token)
        
        expected_headers = {
            "Authorization": f"Bearer {client_settings.github_token}",
            "Accept": "application/vnd.github.v4+json",
            "User-Agent": "github-stars-mcp-server/1.0"
        }
        
        for key, value in expected_headers.items():
            assert client.headers[key] == value

    def test_api_url_configuration(self, client_settings):
        """Test that API URL is configured correctly."""
        client = GitHubClient(client_settings.github_token)
        assert client.base_url == "https://api.github.com/graphql"

    @pytest.mark.asyncio
    async def test_execute_query_with_complex_variables(self, github_client):
        """Test GraphQL query execution with complex variables."""
        mock_response_data = {
            "data": {
                "user": {
                    "starredRepositories": {
                        "edges": [],
                        "pageInfo": {
                            "hasNextPage": False
                        }
                    }
                }
            }
        }
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            query = """
            query($username: String!, $first: Int!, $after: String) {
                user(login: $username) {
                    starredRepositories(first: $first, after: $after) {
                        edges {
                            starredAt
                            node {
                                nameWithOwner
                            }
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
            """
            
            variables = {
                "username": "testuser",
                "first": 10,
                "after": "cursor123"
            }
            
            result = await github_client.query(query, variables)
            
            assert result == mock_response_data["data"]
            
            # Verify complex variables were passed correctly
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["variables"] == variables


class TestGitHubClientIntegration:
    """Integration tests for GitHub client."""
    
    @pytest.fixture
    def client_settings(self):
        """Create test settings for GitHub client."""
        return Settings(
            github_token="test_token_123"
        )
    
    @pytest.fixture
    def integration_github_client(self, client_settings):
        """Create GitHub client for integration tests."""
        return GitHubClient(client_settings.github_token)

    @pytest.mark.asyncio
    async def test_real_query_structure(self, integration_github_client):
        """Test that client can handle real GitHub GraphQL query structures."""
        # This test uses a mock but with real query structure
        real_query = """
        query GetUserStarredRepositories($username: String!, $first: Int!, $after: String) {
            user(login: $username) {
                starredRepositories(first: $first, after: $after, orderBy: {field: STARRED_AT, direction: DESC}) {
                    edges {
                        starredAt
                        node {
                            nameWithOwner
                            description
                            stargazerCount
                            url
                            primaryLanguage {
                                name
                                color
                            }
                            createdAt
                            updatedAt
                            pushedAt
                            isPrivate
                            isFork
                            isArchived
                            owner {
                                login
                                avatarUrl
                                ... on User {
                                    name
                                    bio
                                    location
                                    company
                                    email
                                    createdAt
                                    updatedAt
                                    publicRepos
                                    followers
                                    following
                                }
                                ... on Organization {
                                    name
                                    description
                                    location
                                    email
                                    createdAt
                                    updatedAt
                                }
                            }
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                        hasPreviousPage
                        startCursor
                    }
                    totalCount
                }
            }
        }
        """
        
        mock_response_data = {
            "data": {
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
                                    "primaryLanguage": {
                                        "name": "Python",
                                        "color": "#3572A5"
                                    },
                                    "createdAt": "2011-01-26T19:01:12Z",
                                    "updatedAt": "2023-01-01T00:00:00Z",
                                    "pushedAt": "2023-01-01T00:00:00Z",
                                    "isPrivate": False,
                                    "isFork": False,
                                    "isArchived": False,
                                    "owner": {
                                        "login": "octocat",
                                        "avatarUrl": "https://github.com/images/error/octocat_happy.gif",
                                        "name": "The Octocat",
                                        "bio": "A great octopus",
                                        "location": "San Francisco",
                                        "company": "GitHub",
                                        "email": "octocat@github.com",
                                        "createdAt": "2008-01-14T04:33:35Z",
                                        "updatedAt": "2023-01-01T00:00:00Z",
                                        "publicRepos": 8,
                                        "followers": 3938,
                                        "following": 9
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
        }
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = mock_async_client.return_value.__aenter__.return_value
            mock_client.post = AsyncMock(return_value=mock_response)
            
            variables = {
                "username": "testuser",
                "first": 10,
                "after": None
            }
            
            result = await integration_github_client.query(real_query, variables)
            
            # Verify the structure matches what our models expect
            assert "user" in result
            assert "starredRepositories" in result["user"]
            assert "edges" in result["user"]["starredRepositories"]
            assert "pageInfo" in result["user"]["starredRepositories"]
            assert "totalCount" in result["user"]["starredRepositories"]
            
            # Verify edge structure
            edge = result["user"]["starredRepositories"]["edges"][0]
            assert "starredAt" in edge
            assert "node" in edge
            
            # Verify node structure
            node = edge["node"]
            assert "nameWithOwner" in node
            assert "stargazerCount" in node
            assert "owner" in node