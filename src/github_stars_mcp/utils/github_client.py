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
          id
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

README_QUERY = """
query GetRepositoryReadme($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    nameWithOwner
    url
    readme {
      ... on Blob {
        text
      }
    }
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
        if not self.token:
            raise ValueError("GitHub token is required")
            
        self.base_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v4+json",
            "User-Agent": "github-stars-mcp-server/1.0"
        }
        
        # Cache for current user info
        self._current_user_cache: Optional[Dict[str, Any]] = None
        self._current_user_cache_time: Optional[float] = None
        self._cache_ttl = 300  # 5 minutes

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
            username: GitHub username. If empty, uses authenticated user.
            cursor: Pagination cursor for fetching next page

        Returns:
            Dictionary containing starred repositories data with pagination info
        """
        
        # If username is empty, use authenticated user
        actual_username = username
        if not username or username.strip() == "":
            current_user = await self.get_current_user()
            if not current_user:
                logger.error("Cannot get current user for empty username")
                raise AuthenticationError("Failed to get authenticated user information")
            actual_username = current_user.get("login")

            if not actual_username:
                logger.error("Current user has no login field")
                raise AuthenticationError("Current user information is incomplete")
            logger.info("Using authenticated user", username=actual_username)
            
        logger.info("Fetching starred repositories", username=actual_username, cursor=cursor)
        
        variables = {"username": actual_username, "cursor": cursor}
        data = await self.query(STARRED_REPOS_QUERY, variables)
        logger.debug("Starred repositories data", data=data)
        user_data = data.get("user")
        if not user_data:
            logger.warning("User not found", username=actual_username)
            return {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
            
        starred_data = user_data.get("starredRepositories", {})
        return starred_data


    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user information with caching.
        
        Returns:
            Current user information or None if authentication fails
        """
        import time
        
        # Check cache first
        current_time = time.time()
        if (self._current_user_cache is not None and 
            self._current_user_cache_time is not None and 
            current_time - self._current_user_cache_time < self._cache_ttl):
            logger.info("Using cached current user info", username=self._current_user_cache.get("login"))
            return self._current_user_cache
        
        logger.info("Fetching current user info from API")
        
        try:
            data = await self.query(CURRENT_USER_QUERY)
            
            user_data = data.get("viewer")
            if user_data:
                # Cache the result
                self._current_user_cache = user_data
                self._current_user_cache_time = current_time
                logger.info("Current user info fetched and cached successfully", username=user_data.get("login"))
            else:
                logger.warning("Failed to fetch current user info")
                
            return user_data
        except Exception as e:
            logger.error("Error fetching current user info", error=str(e))
            return None
    
    async def get_repository_readme(self, owner: str, name: str) -> Dict[str, Any]:
        """Get README content for a repository.
        
        Args:
            owner: Repository owner
            name: Repository name
            
        Returns:
            Dictionary containing README content and metadata
        """
        logger.info("Fetching repository README", owner=owner, name=name)
        
        variables = {"owner": owner, "name": name}
        
        try:
            data = await self.query(README_QUERY, variables)
            
            repo_data = data.get("repository")
            if not repo_data:
                logger.warning("Repository not found", owner=owner, name=name)
                return {
                    "content": None,
                    "size": None,
                    "has_readme": False,
                    "error": "Repository not found"
                }
            
            readme_obj = repo_data.get("object")
            if readme_obj and readme_obj.get("text"):
                logger.info("README.md found", owner=owner, name=name, size=readme_obj.get("byteSize"))
                return {
                    "content": readme_obj["text"],
                    "size": readme_obj.get("byteSize"),
                    "has_readme": True,
                    "error": None
                }
            
            # Try to find alternative README files
            alternatives = repo_data.get("readmeAlternatives", {})
            entries = alternatives.get("entries", [])
            
            readme_files = [
                entry["name"] for entry in entries 
                if entry["type"] == "blob" and entry["name"].lower().startswith("readme")
            ]
            
            if readme_files:
                # Try the first alternative README file
                alt_readme = readme_files[0]
                logger.info("Trying alternative README file", owner=owner, name=name, filename=alt_readme)
                
                # Query for the alternative README
                alt_query = f"""
                query GetAlternativeReadme($owner: String!, $name: String!) {{
                  repository(owner: $owner, name: $name) {{
                    object(expression: "HEAD:{alt_readme}") {{
                      ... on Blob {{
                        text
                        byteSize
                      }}
                    }}
                  }}
                }}
                """
                
                alt_data = await self.query(alt_query, variables)
                alt_repo = alt_data.get("repository", {})
                alt_obj = alt_repo.get("object")
                
                if alt_obj and alt_obj.get("text"):
                    logger.info("Alternative README found", owner=owner, name=name, filename=alt_readme)
                    return {
                        "content": alt_obj["text"],
                        "size": alt_obj.get("byteSize"),
                        "has_readme": True,
                        "error": None
                    }
            
            logger.info("No README found", owner=owner, name=name)
            return {
                "content": None,
                "size": None,
                "has_readme": False,
                "error": None
            }
            
        except Exception as e:
            logger.error("Failed to fetch README", owner=owner, name=name, error=str(e))
            return {
                "content": None,
                "size": None,
                "has_readme": False,
                "error": str(e)
            }



# Global client instance
client = GitHubClient()

