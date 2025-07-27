"""Integration tests for MCP tools with real-world scenarios."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp import Context

from github_stars_mcp.tools.starred_repo_list import get_user_starred_repositories
from github_stars_mcp.tools.repo_details import get_repo_details
from github_stars_mcp.tools.batch_repo_details import get_batch_repo_details
from github_stars_mcp.tools.analysis_bundle import create_full_analysis_bundle
from github_stars_mcp.models import (
    StarredRepositoriesResponse,
    StartedRepository,
    RepositoryDetails,
    BatchRepositoryDetailsResponse,
    StarredRepositoriesWithReadmeResponse
)
from github_stars_mcp.exceptions import GitHubAPIError, ValidationError


class TestToolsWorkflow:
    """Test realistic workflows using multiple tools together."""

    @pytest.fixture
    def sample_starred_repos(self):
        """Sample starred repositories for workflow testing."""
        return [
            StartedRepository(
                id="repo1",
                nameWithOwner="microsoft/vscode",
                name="vscode",
                owner="microsoft",
                description="Visual Studio Code",
                stargazerCount=162000,
                url="https://github.com/microsoft/vscode",
                primaryLanguage="TypeScript",
                starredAt="2023-01-01T00:00:00Z"
            ),
            StartedRepository(
                id="repo2",
                nameWithOwner="python/cpython",
                name="cpython",
                owner="python",
                description="The Python programming language",
                stargazerCount=62000,
                url="https://github.com/python/cpython",
                primaryLanguage="Python",
                starredAt="2023-01-02T00:00:00Z"
            )
        ]

    @pytest.fixture
    def sample_repo_details(self):
        """Sample repository details for workflow testing."""
        return {
            "microsoft/vscode": RepositoryDetails(
                readme_content="# Visual Studio Code\n\nCode editing. Redefined."
            ),
            "python/cpython": RepositoryDetails(
                readme_content="# CPython\n\nThis is the home of the Python programming language."
            )
        }

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, mock_context, sample_starred_repos, sample_repo_details):
        """Test complete workflow: get starred repos -> get details -> create bundle."""
        # Mock starred repositories response
        starred_response = StarredRepositoriesResponse(
            repositories=sample_starred_repos,
            total_count=2,
            has_next_page=False,
            end_cursor=""
        )
        
        # Mock batch details response
        batch_response = BatchRepositoryDetailsResponse(data=sample_repo_details)
        
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_starred_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'), \
             patch('github_stars_mcp.tools.batch_repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.batch_repo_details.fetch_multi_repository_details') as mock_batch_fetch:
            
            # Setup mocks
            mock_starred_request.return_value = {
                "edges": [
                    {
                        "starredAt": "2023-01-01T00:00:00Z",
                        "node": {
                            "id": "repo1",
                            "nameWithOwner": "microsoft/vscode",
                            "description": "Visual Studio Code",
                            "stargazerCount": 162000,
                            "url": "https://github.com/microsoft/vscode",
                            "primaryLanguage": {"name": "TypeScript"},
                            "repositoryTopics": {"nodes": []},
                            "languages": {"edges": []}
                        }
                    },
                    {
                        "starredAt": "2023-01-02T00:00:00Z",
                        "node": {
                            "id": "repo2",
                            "nameWithOwner": "python/cpython",
                            "description": "The Python programming language",
                            "stargazerCount": 62000,
                            "url": "https://github.com/python/cpython",
                            "primaryLanguage": {"name": "Python"},
                            "repositoryTopics": {"nodes": []},
                            "languages": {"edges": []}
                        }
                    }
                ],
                "totalCount": 2,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            mock_batch_fetch.return_value = batch_response
            
            # Step 1: Get starred repositories
            starred_result = await get_user_starred_repositories(mock_context, "testuser")
            assert len(starred_result.repositories) == 2
            
            # Step 2: Get batch details for the repositories
            repo_ids = [repo.nameWithOwner for repo in starred_result.repositories]
            batch_result = await get_batch_repo_details(mock_context, repo_ids)
            assert len(batch_result.data) == 2
            
            # Step 3: Create full analysis bundle
            bundle_result = await create_full_analysis_bundle(mock_context, "testuser")
            assert isinstance(bundle_result, StarredRepositoriesWithReadmeResponse)
            assert bundle_result.total_count == 2

    @pytest.mark.asyncio
    async def test_pagination_workflow(self, mock_context):
        """Test workflow with pagination handling."""
        # First page response
        first_page_response = {
            "edges": [
                {
                    "starredAt": "2023-01-01T00:00:00Z",
                    "node": {
                        "id": "repo1",
                        "nameWithOwner": "user/repo1",
                        "repositoryTopics": {"nodes": []},
                        "languages": {"edges": []}
                    }
                }
            ],
            "totalCount": 2,
            "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"}
        }
        
        # Second page response
        second_page_response = {
            "edges": [
                {
                    "starredAt": "2023-01-02T00:00:00Z",
                    "node": {
                        "id": "repo2",
                        "nameWithOwner": "user/repo2",
                        "repositoryTopics": {"nodes": []},
                        "languages": {"edges": []}
                    }
                }
            ],
            "totalCount": 2,
            "pageInfo": {"hasNextPage": False, "endCursor": ""}
        }
        
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'):
            
            # Mock sequential responses for pagination
            mock_request.side_effect = [first_page_response, second_page_response]
            
            # Get first page
            first_result = await get_user_starred_repositories(mock_context, "testuser")
            assert len(first_result.repositories) == 1
            assert first_result.has_next_page is True
            assert first_result.end_cursor == "cursor1"
            
            # Get second page
            second_result = await get_user_starred_repositories(mock_context, "testuser", "cursor1")
            assert len(second_result.repositories) == 1
            assert second_result.has_next_page is False

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_context):
        """Test workflow with error handling and recovery."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'):
            
            # First call fails
            mock_request.side_effect = [GitHubAPIError("Rate limit exceeded"), {
                "edges": [],
                "totalCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }]
            
            # First attempt should fail
            with pytest.raises(GitHubAPIError):
                await get_user_starred_repositories(mock_context, "testuser")
            
            # Second attempt should succeed
            result = await get_user_starred_repositories(mock_context, "testuser")
            assert isinstance(result, StarredRepositoriesResponse)

    @pytest.mark.asyncio
    async def test_large_dataset_workflow(self, mock_context):
        """Test workflow with large dataset handling."""
        # Create a large list of repository IDs
        large_repo_list = [f"user/repo{i}" for i in range(50)]
        
        # Mock batch processing
        mock_batch_data = {
            repo_id: RepositoryDetails(readme_content=f"# {repo_id}")
            for repo_id in large_repo_list
        }
        
        with patch('github_stars_mcp.tools.batch_repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.batch_repo_details.fetch_multi_repository_details') as mock_fetch:
            
            mock_fetch.return_value = BatchRepositoryDetailsResponse(data=mock_batch_data)
            
            result = await get_batch_repo_details(mock_context, large_repo_list)
            
            assert len(result.data) == 50
            assert all(f"user/repo{i}" in result.data for i in range(50))

    @pytest.mark.asyncio
    async def test_mixed_success_failure_workflow(self, mock_context):
        """Test workflow where some operations succeed and others fail."""
        repo_ids = ["valid/repo", "invalid/repo", "another/valid"]
        
        # Mock partial success in batch operation
        partial_data = {
            "valid/repo": RepositoryDetails(readme_content="# Valid Repo"),
            "another/valid": RepositoryDetails(readme_content="# Another Valid")
            # "invalid/repo" is missing (simulating failure)
        }
        
        with patch('github_stars_mcp.tools.batch_repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.batch_repo_details.fetch_multi_repository_details') as mock_fetch:
            
            mock_fetch.return_value = BatchRepositoryDetailsResponse(data=partial_data)
            
            result = await get_batch_repo_details(mock_context, repo_ids)
            
            # Should return partial results
            assert len(result.data) == 2
            assert "valid/repo" in result.data
            assert "another/valid" in result.data
            assert "invalid/repo" not in result.data


class TestToolsPerformance:
    """Performance-related tests for MCP tools."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, mock_context):
        """Test that tools can handle concurrent requests properly."""
        import asyncio
        
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'):
            
            mock_request.return_value = {
                "edges": [],
                "totalCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # Create multiple concurrent requests
            tasks = [
                get_user_starred_repositories(mock_context, f"user{i}")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert all(isinstance(result, StarredRepositoriesResponse) for result in results)

    @pytest.mark.asyncio
    async def test_memory_efficient_processing(self, mock_context):
        """Test that tools process large datasets efficiently."""
        # Simulate processing a large number of repositories
        large_repo_count = 1000
        
        with patch('github_stars_mcp.tools.analysis_bundle._fetch_all_starred_repositories') as mock_fetch_starred, \
             patch('github_stars_mcp.tools.analysis_bundle._fetch_repository_details') as mock_fetch_details:
            
            # Mock large dataset
            mock_starred_map = {
                f"repo{i}": MagicMock()
                for i in range(large_repo_count)
            }
            mock_fetch_starred.return_value = mock_starred_map
            mock_fetch_details.return_value = {}
            
            result = await create_full_analysis_bundle(mock_context, "testuser")
            
            # Should handle large dataset without issues
            assert result.total_count == large_repo_count


class TestToolsEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_responses(self, mock_context):
        """Test tools behavior with empty responses."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'):
            
            mock_request.return_value = {
                "edges": [],
                "totalCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            result = await get_user_starred_repositories(mock_context, "emptyuser")
            
            assert result.total_count == 0
            assert len(result.repositories) == 0
            assert result.has_next_page is False

    @pytest.mark.asyncio
    async def test_malformed_data_handling(self, mock_context):
        """Test tools behavior with malformed data."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'):
            
            # Malformed response missing required fields
            mock_request.return_value = {
                "edges": [
                    {
                        "node": {
                            "id": "repo1",
                            "nameWithOwner": "user/repo"
                            # Missing other required fields
                        }
                    }
                ],
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # Should handle gracefully
            result = await get_user_starred_repositories(mock_context, "testuser")
            assert len(result.repositories) == 1

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, mock_context):
        """Test tools behavior with unicode and special characters."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username'):
            
            mock_request.return_value = {
                "edges": [
                    {
                        "starredAt": "2023-01-01T00:00:00Z",
                        "node": {
                            "id": "repo1",
                            "nameWithOwner": "用户/项目",
                            "description": "这是一个测试项目 🚀",
                            "repositoryTopics": {"nodes": []},
                            "languages": {"edges": []}
                        }
                    }
                ],
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            result = await get_user_starred_repositories(mock_context, "testuser")
            
            assert len(result.repositories) == 1
            assert result.repositories[0].nameWithOwner == "用户/项目"
            assert "🚀" in result.repositories[0].description

    @pytest.mark.asyncio
    async def test_boundary_values(self, mock_context):
        """Test tools with boundary values."""
        # Test with maximum allowed batch size
        max_repo_ids = [f"user/repo{i}" for i in range(100)]  # MAX_BATCH_SIZE
        
        with patch('github_stars_mcp.tools.batch_repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.batch_repo_details.fetch_multi_repository_details') as mock_fetch:
            
            mock_fetch.return_value = BatchRepositoryDetailsResponse(data={})
            
            # Should succeed with max batch size
            result = await get_batch_repo_details(mock_context, max_repo_ids)
            assert isinstance(result, BatchRepositoryDetailsResponse)
            
            # Should fail with over max batch size
            over_max_repo_ids = [f"user/repo{i}" for i in range(101)]
            with pytest.raises(ValidationError):
                await get_batch_repo_details(mock_context, over_max_repo_ids)