"""GitHub API client module."""

import asyncio
from typing import Dict, Any, Optional, List

import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..config import settings
from ..exceptions import GitHubAPIError, AuthenticationError, RateLimitError

# Configure structured logging
logger = structlog.get_logger(__name__)

# GraphQL query constants
STARRED_REPOS_QUERY = """
query GetStarredRepositories($username: String!, $cursor: String) {
  user(login: $username) {
    starredRepositories(
      first: 100
      after: $cursor
      orderBy: { field: STARRED_AT, direction: DESC }
    ) {
      pageInfo {
        endCursor
        hasNextPage
      }
      edges {
        cursor
        starredAt
        node {
          nameWithOwner
          description
          stargazerCount
          url
          diskUsage
          pushedAt
          forkCount
          primaryLanguage {
            name
          }
          repositoryTopics(first: 10) {
            nodes {
              topic {
                name
              }
            }
          }
          languages(first: 5, orderBy: { field: SIZE, direction: DESC }) {
            edges {
              size
              node {
                name 
                color 
              }
            }
          }
        }
      }
    }
  }
}

"""

CURRENT_USER_QUERY = """
query GetCurrentUser {
  viewer {
    login
    name
    avatarUrl
  }
}
"""


class GitHubClient:
    """Async GitHub API client with GraphQL support.
    
    This client provides methods for querying GitHub's GraphQL API
    with proper authentication, error handling, and retry logic.
    """
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client.
        
        Args:
            token: GitHub personal access token. If not provided, uses settings.github_token
        """
        self.token = token or settings.github_token
        self.base_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v4+json",
            "User-Agent": "github-stars-mcp-server/1.0"
        }
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against GitHub API.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            GraphQL response data
            
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            GitHubAPIError: For other API errors
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        logger.info("Executing GraphQL query", query_type=query.split()[1] if query.split() else "unknown")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                
                # Handle HTTP errors
                if response.status_code == 401:
                    logger.error("Authentication failed", status_code=response.status_code)
                    raise AuthenticationError("Invalid GitHub token")
                elif response.status_code == 403:
                    # Check if it's a rate limit error
                    if "rate limit" in response.text.lower():
                        logger.warning("Rate limit exceeded", status_code=response.status_code)
                        raise RateLimitError("GitHub API rate limit exceeded")
                    else:
                        logger.error("Forbidden access", status_code=response.status_code)
                        raise GitHubAPIError(f"Forbidden: {response.text}")
                elif response.status_code >= 400:
                    logger.error("HTTP error", status_code=response.status_code, response_text=response.text)
                    raise GitHubAPIError(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                # Handle GraphQL errors
                if "errors" in data:
                    errors = data["errors"]
                    logger.error("GraphQL errors", errors=errors)
                    error_messages = [error.get("message", "Unknown error") for error in errors]
                    raise GitHubAPIError(f"GraphQL errors: {'; '.join(error_messages)}")
                
                logger.info("GraphQL query successful")
                return data.get("data", {})
                
            except httpx.RequestError as e:
                logger.error("Request error", error=str(e))
                raise GitHubAPIError(f"Request failed: {str(e)}")
            except httpx.TimeoutException as e:
                logger.error("Request timeout", error=str(e))
                raise GitHubAPIError(f"Request timeout: {str(e)}")
    
    async def get_user_starred_repositories(self, username: str, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get starred repositories for a user with pagination support.
        
        Args:
            username: GitHub username
            cursor: Pagination cursor for fetching next page
            
        Returns:
            Dictionary containing starred repositories data with pagination info
        """
        logger.info("Fetching starred repositories", username=username, cursor=cursor)
        
        variables = {"username": username, "cursor": cursor}
        data = await self.query(STARRED_REPOS_QUERY, variables)
        
        user_data = data.get("user")
        if not user_data:
            logger.warning("User not found", username=username)
            return {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
            
        starred_data = user_data.get("starredRepositories", {})
        return starred_data


    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user information.
        
        Returns:
            Current user information or None if authentication fails
        """
        logger.info("Fetching current user info")
        
        data = await self.query(CURRENT_USER_QUERY)
        
        user_data = data.get("viewer")
        if user_data:
            logger.info("Current user info fetched successfully", username=user_data.get("login"))
        else:
            logger.warning("Failed to fetch current user info")
            
        return user_data



# Global client instance
client = GitHubClient()

