"""Performance tests for MCP tools."""

import pytest
import asyncio
import time
import os
import sys
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

from github_stars_mcp.tools.starred_repo_list import get_user_starred_repositories
from github_stars_mcp.tools.repo_details import get_repo_details
from github_stars_mcp.tools.batch_repo_details import get_batch_repo_details
from github_stars_mcp.tools.analysis_bundle import create_full_analysis_bundle
from github_stars_mcp.models import (
    StarredRepositoriesResponse,
    StartedRepository,
    BatchRepositoryDetailsResponse,
    RepositoryDetails
)


class TestPerformance:
    """Performance tests for MCP tools."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FastMCP context for testing."""
        context = AsyncMock()
        context.info = AsyncMock()
        context.error = AsyncMock()
        context.debug = AsyncMock()
        return context

    @pytest.fixture
    def large_repository_list(self):
        """Create a large list of repositories for testing."""
        return [f"user/repo{i}" for i in range(1000)]

    @pytest.fixture
    def mock_starred_response_large(self):
        """Create a large mock starred repositories response."""
        return StarredRepositoriesResponse(
            repositories=[
                StartedRepository(
                    id=f"repo{i}",
                    nameWithOwner=f"user/repo{i}",
                    name=f"repo{i}",
                    owner="user",
                    stargazerCount=100 + i,
                    url=f"https://github.com/user/repo{i}"
                ) for i in range(1000)
            ],
            total_count=1000,
            has_next_page=False,
            end_cursor=""
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_starred_repositories_response_time(self, mock_context):
        """Test response time for getting starred repositories."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_validate.return_value = "testuser"
            mock_request.return_value = {
                "edges": [{"node": {"id": f"repo{i}", "nameWithOwner": f"user/repo{i}"}} for i in range(100)],
                "totalCount": 100,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # Measure response time
            start_time = time.perf_counter()
            result = await get_user_starred_repositories(mock_context, "testuser")
            end_time = time.perf_counter()
            
            response_time = end_time - start_time
            
            # Should complete within reasonable time (< 1 second for mocked response)
            assert response_time < 1.0
            assert len(result.repositories) == 100
            
            print(f"Starred repositories response time: {response_time:.4f} seconds")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_processing_performance(self, mock_context, large_repository_list):
        """Test performance of batch repository processing."""
        # Limit to 100 repos for performance test
        repo_list = large_repository_list[:100]
        
        mock_response = BatchRepositoryDetailsResponse(data={
            repo_id: RepositoryDetails(
                readme_content=f"# {repo_id}\nThis is a test repository.",
                description=f"Description for {repo_id}",
                topics=["python", "test"],
                languages=["Python"]
            ) for repo_id in repo_list
        })
        
        with patch('github_stars_mcp.tools.batch_repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.batch_repo_details.fetch_multi_repository_details') as mock_fetch:
            
            mock_fetch.return_value = mock_response
            
            # Measure processing time
            start_time = time.perf_counter()
            result = await get_batch_repo_details(mock_context, repo_list)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            
            # Should process 100 repos within reasonable time
            assert processing_time < 5.0  # 5 seconds max
            assert len(result.data) == 100
            
            # Calculate throughput
            throughput = len(repo_list) / processing_time
            print(f"Batch processing time: {processing_time:.4f} seconds")
            print(f"Throughput: {throughput:.2f} repos/second")
            
            # Should achieve reasonable throughput
            assert throughput > 20  # At least 20 repos per second

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_requests_performance(self, mock_context):
        """Test performance under concurrent requests."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_validate.return_value = "testuser"
            mock_request.return_value = {
                "edges": [{"node": {"id": f"repo{i}", "nameWithOwner": f"user/repo{i}"}} for i in range(10)],
                "totalCount": 10,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # Create multiple concurrent requests
            num_concurrent = 10
            
            start_time = time.perf_counter()
            
            tasks = [
                get_user_starred_repositories(mock_context, f"user{i}")
                for i in range(num_concurrent)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # All requests should complete successfully
            assert len(results) == num_concurrent
            assert all(len(result.repositories) == 10 for result in results)
            
            # Concurrent execution should be faster than sequential
            # (assuming some parallelization benefit)
            average_time_per_request = total_time / num_concurrent
            print(f"Concurrent requests total time: {total_time:.4f} seconds")
            print(f"Average time per request: {average_time_per_request:.4f} seconds")
            
            # Should complete all requests within reasonable time
            assert total_time < 5.0

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    async def test_memory_usage_monitoring(self, mock_context):
        """Test memory usage during operations."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large mock data
        large_repo_list = [f"user/repo{i}" for i in range(500)]
        
        mock_response = BatchRepositoryDetailsResponse(data={
            repo_id: RepositoryDetails(
                readme_content="# Large README\n" + "Content " * 1000,  # ~7KB per repo
                description=f"Description for {repo_id}",
                topics=["python", "test", "performance"],
                languages=["Python", "JavaScript"]
            ) for repo_id in large_repo_list
        })
        
        with patch('github_stars_mcp.tools.batch_repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.batch_repo_details.fetch_multi_repository_details') as mock_fetch:
            
            mock_fetch.return_value = mock_response
            
            # Process the data
            result = await get_batch_repo_details(mock_context, large_repo_list)
            
            # Measure memory after processing
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"Initial memory: {initial_memory:.2f} MB")
            print(f"Final memory: {final_memory:.2f} MB")
            print(f"Memory increase: {memory_increase:.2f} MB")
            
            # Verify processing completed successfully
            assert len(result.data) == 500
            
            # Memory increase should be reasonable (less than 100MB for this test)
            assert memory_increase < 100

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_analysis_bundle_performance(self, mock_context):
        """Test performance of full analysis bundle creation."""
        # Mock starred repositories response
        starred_response = StarredRepositoriesResponse(
            repositories=[
                StartedRepository(
                    id=f"repo{i}",
                    nameWithOwner=f"user/repo{i}",
                    name=f"repo{i}",
                    owner="user",
                    stargazerCount=100 + i,
                    url=f"https://github.com/user/repo{i}"
                ) for i in range(50)  # 50 repos for performance test
            ],
            total_count=50,
            has_next_page=False,
            end_cursor=""
        )
        
        # Mock batch details response
        batch_response = BatchRepositoryDetailsResponse(data={
            f"user/repo{i}": RepositoryDetails(
                readme_content=f"# Repository {i}\nDetailed description.",
                description=f"Repository {i} description",
                topics=["python", "test"],
                languages=["Python"]
            ) for i in range(50)
        })
        
        with patch('github_stars_mcp.tools.analysis_bundle.get_user_starred_repositories') as mock_starred, \
             patch('github_stars_mcp.tools.analysis_bundle.get_batch_repo_details') as mock_batch:
            
            mock_starred.return_value = starred_response
            mock_batch.return_value = batch_response
            
            # Measure analysis bundle creation time
            start_time = time.perf_counter()
            result = await create_full_analysis_bundle(mock_context, "testuser")
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            
            # Verify result
            assert result is not None
            # Note: Actual result structure depends on implementation
            # This is a placeholder test that should be updated based on actual return type
            
            print(f"Analysis bundle creation time: {processing_time:.4f} seconds")
            
            # Should complete within reasonable time
            assert processing_time < 10.0  # 10 seconds max for 50 repos

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_error_handling_performance(self, mock_context):
        """Test performance impact of error handling."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client') as mock_ensure:
            # Simulate API errors
            mock_ensure.side_effect = Exception("API Error")
            
            # Measure error handling time
            start_time = time.perf_counter()
            
            with pytest.raises(Exception):
                await get_user_starred_repositories(mock_context, "testuser")
            
            end_time = time.perf_counter()
            error_handling_time = end_time - start_time
            
            print(f"Error handling time: {error_handling_time:.4f} seconds")
            
            # Error handling should be fast
            assert error_handling_time < 1.0

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_pagination_performance(self, mock_context):
        """Test performance of pagination handling."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_validate.return_value = "testuser"
            
            # Simulate multiple pages
            page_responses = [
                {
                    "edges": [{"node": {"id": f"repo{i+page*50}", "nameWithOwner": f"user/repo{i+page*50}"}} for i in range(50)],
                    "totalCount": 200,
                    "pageInfo": {"hasNextPage": page < 3, "endCursor": f"cursor{page}"}
                }
                for page in range(4)  # 4 pages of 50 repos each
            ]
            
            mock_request.side_effect = page_responses
            
            # Measure pagination performance
            start_time = time.perf_counter()
            
            all_repos = []
            cursor = ""
            
            for page in range(4):
                result = await get_user_starred_repositories(mock_context, "testuser", cursor=cursor)
                all_repos.extend(result.repositories)
                cursor = result.end_cursor
                
                if not result.has_next_page:
                    break
            
            end_time = time.perf_counter()
            pagination_time = end_time - start_time
            
            print(f"Pagination time for 4 pages: {pagination_time:.4f} seconds")
            print(f"Total repositories collected: {len(all_repos)}")
            
            # Should handle pagination efficiently
            assert pagination_time < 5.0
            assert len(all_repos) == 200

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_data_serialization_performance(self, mock_context):
        """Test performance of data serialization/deserialization."""
        import json
        
        # Create large data structure
        large_data = {
            f"user/repo{i}": {
                "readme_content": "# Large README\n" + "Content " * 500,
                "description": f"Description for repo {i}",
                "topics": ["python", "test", "performance", "data"],
                "languages": ["Python", "JavaScript", "TypeScript"]
            } for i in range(100)
        }
        
        # Measure serialization time
        start_time = time.perf_counter()
        serialized = json.dumps(large_data)
        serialization_time = time.perf_counter() - start_time
        
        # Measure deserialization time
        start_time = time.perf_counter()
        deserialized = json.loads(serialized)
        deserialization_time = time.perf_counter() - start_time
        
        print(f"Serialization time: {serialization_time:.4f} seconds")
        print(f"Deserialization time: {deserialization_time:.4f} seconds")
        print(f"Data size: {len(serialized) / 1024 / 1024:.2f} MB")
        
        # Verify data integrity
        assert len(deserialized) == 100
        assert deserialized == large_data
        
        # Should serialize/deserialize efficiently
        assert serialization_time < 2.0
        assert deserialization_time < 2.0


class TestLoadTesting:
    """Load testing for MCP tools."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FastMCP context for testing."""
        context = AsyncMock()
        context.info = AsyncMock()
        context.error = AsyncMock()
        context.debug = AsyncMock()
        return context

    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_high_concurrency_load(self, mock_context):
        """Test system behavior under high concurrency load."""
        with patch('github_stars_mcp.tools.starred_repo_list.ensure_github_client'), \
             patch('github_stars_mcp.tools.starred_repo_list.safe_github_request') as mock_request, \
             patch('github_stars_mcp.tools.starred_repo_list.validate_github_username') as mock_validate:
            
            mock_validate.return_value = "testuser"
            mock_request.return_value = {
                "edges": [{"node": {"id": "repo1", "nameWithOwner": "user/repo1"}}],
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # High concurrency test
            num_concurrent = 100
            
            start_time = time.perf_counter()
            
            tasks = [
                get_user_starred_repositories(mock_context, f"user{i}")
                for i in range(num_concurrent)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Count successful vs failed requests
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful
            
            print(f"High concurrency load test:")
            print(f"Total requests: {num_concurrent}")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Total time: {total_time:.4f} seconds")
            print(f"Requests per second: {num_concurrent / total_time:.2f}")
            
            # Most requests should succeed
            success_rate = successful / num_concurrent
            assert success_rate > 0.95  # 95% success rate
            
            # Should handle high load reasonably
            assert total_time < 30.0  # 30 seconds max

    @pytest.mark.asyncio
    @pytest.mark.load
    @pytest.mark.slow
    async def test_sustained_load(self, mock_context):
        """Test system behavior under sustained load."""
        with patch('github_stars_mcp.tools.repo_details.ensure_github_client'), \
             patch('github_stars_mcp.tools.repo_details.fetch_repository_details') as mock_fetch:
            
            mock_fetch.return_value = RepositoryDetails(
                readme_content="# Test Repository",
                description="Test description",
                topics=["test"],
                languages=["Python"]
            )
            
            # Sustained load test - multiple batches over time
            batch_size = 20
            num_batches = 10
            delay_between_batches = 0.5  # seconds
            
            all_results = []
            start_time = time.perf_counter()
            
            for batch in range(num_batches):
                batch_start = time.perf_counter()
                
                tasks = [
                    get_repo_details(mock_context, f"user/repo{batch}_{i}")
                    for i in range(batch_size)
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)
                
                batch_time = time.perf_counter() - batch_start
                print(f"Batch {batch + 1}/{num_batches} completed in {batch_time:.4f}s")
                
                # Small delay between batches
                if batch < num_batches - 1:
                    await asyncio.sleep(delay_between_batches)
            
            total_time = time.perf_counter() - start_time
            
            # Analyze results
            total_requests = batch_size * num_batches
            successful = sum(1 for r in all_results if not isinstance(r, Exception))
            
            print(f"Sustained load test results:")
            print(f"Total requests: {total_requests}")
            print(f"Successful: {successful}")
            print(f"Total time: {total_time:.4f} seconds")
            print(f"Average requests per second: {total_requests / total_time:.2f}")
            
            # Should maintain good performance over time
            success_rate = successful / total_requests
            assert success_rate > 0.98  # 98% success rate
            assert total_time < 60.0  # Should complete within 1 minute


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short"
    ])