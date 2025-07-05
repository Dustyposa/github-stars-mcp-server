"""GitHub API client module.

This module provides an async GitHub API client with authentication,
GraphQL query support, caching, and error handling capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import settings
from ..exceptions import GitHubAPIError, RateLimitError, AuthenticationError

# Configure structured logging
logger = structlog.get_logger(__name__)

# GraphQL query constants
STARRED_REPOS_QUERY = """
query GetStarredRepositories($username: String!, $cursor: String) {
  user(login: $username) {
    starredRepositories(first: 100, after: $cursor, orderBy: {field: STARRED_AT, direction: DESC}) {
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
          primaryLanguage {
            name
            color
          }
          repositoryTopics(first: 5) {
            nodes {
              topic {
                name
              }
            }
          }

        }
      }
    }
  }
}
"""

USER_INFO_QUERY = """
query GetUserInfo($username: String!) {
  user(login: $username) {
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
    
    async def get_user_starred_repositories(self, username: str) -> List[Dict[str, Any]]:
        """Get all starred repositories for a user with pagination.
        
        Args:
            username: GitHub username
            
        Returns:
            List of starred repository data
        """
        all_repos = []
        has_next_page = True
        cursor = None
        
        logger.info("Fetching starred repositories", username=username)
        
        while has_next_page:
            variables = {"username": username, "cursor": cursor}
            data = await self.query(STARRED_REPOS_QUERY, variables)
            
            user_data = data.get("user")
            if not user_data:
                logger.warning("User not found", username=username)
                break
                
            starred_data = user_data.get("starredRepositories", {})
            edges = starred_data.get("edges", [])
            all_repos.extend(edges)
            
            page_info = starred_data.get("pageInfo", {})
            # has_next_page = page_info.get("hasNextPage", False)
            has_next_page = False
            cursor = page_info.get("endCursor")
            
            logger.debug("Fetched page", repos_count=len(edges), has_next_page=has_next_page)

            # Add a small delay to be respectful to the API
            if has_next_page:
                await asyncio.sleep(0.1)
        
        logger.info("Completed fetching starred repositories", username=username, total_repos=len(all_repos))
        return all_repos
    
    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information.
        
        Args:
            username: GitHub username
            
        Returns:
            User information or None if user not found
        """
        logger.info("Fetching user info", username=username)
        
        variables = {"username": username}
        data = await self.query(USER_INFO_QUERY, variables)
        
        user_data = data.get("user")
        if user_data:
            logger.info("User info fetched successfully", username=username)
        else:
            logger.warning("User not found", username=username)
            
        return user_data

    async def get_starred_repositories_page(self, username: str, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get a single page of starred repositories for a user.

        Args:
            username: GitHub username
            cursor: Pagination cursor (optional)

        Returns:
            A dict containing:
            - 'repos': list of repository data
            - 'has_next_page': bool
            - 'cursor': next page cursor
        """
        logger.info("Fetching starred repositories page", username=username, cursor=cursor)

        variables = {"username": username, "cursor": cursor}
        data = await self.query(STARRED_REPOS_QUERY, variables)

        user_data = data.get("user")
        if not user_data:
            logger.warning("User not found", username=username)
            return {
                "repos": [],
                "has_next_page": False,
                "cursor": None
            }

        starred_data = user_data.get("starredRepositories", {})
        nodes = starred_data.get("nodes", [])
        page_info = starred_data.get("pageInfo", {})

        result = {
            "repos": nodes,
            "has_next_page": page_info.get("hasNextPage", False),
            "cursor": page_info.get("endCursor"),
        }

        logger.debug("Fetched page", repos_count=len(nodes), has_next_page=result["has_next_page"])
        return result

# Global client instance
client = GitHubClient()

