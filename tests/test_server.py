"""Tests for MCP server functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from github_stars_mcp.server import mcp
from github_stars_mcp.config import Settings


class TestMCPServer:
    """Test cases for MCP server functionality."""

    @pytest.fixture
    def test_settings(self):
        """Create test settings for server testing."""
        return Settings(
            github_token="test_token_123",
            cache_dir=".test_cache",
            log_level="DEBUG"
        )

    def test_server_initialization(self):
        """Test that MCP server initializes correctly."""
        assert mcp is not None
        assert hasattr(mcp, 'name')
        assert mcp.name == "GitHub Stars MCP Server"

    @pytest.mark.asyncio
    async def test_server_tools_registration(self):
        """Test that all tools are properly registered with the server."""
        tools = await mcp.get_tools()
        
        # Check that we have the expected number of tools
        assert len(tools) >= 4
        
        # Check for specific tool names
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_user_starred_repositories",
            "get_repo_details",
            "get_batch_repo_details",
            "create_full_analysis_bundle"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that tool schemas are properly defined."""
        tools = await mcp.get_tools()
        
        for tool in tools:
            # Each tool should have a name
            assert hasattr(tool, 'name')
            assert tool.name is not None
            
            # Each tool should have a description
            assert hasattr(tool, 'description')
            assert tool.description is not None
            
            # Each tool should have parameters schema
            assert hasattr(tool, 'parameters')
            assert tool.parameters is not None
            
            # Parameters should be a valid JSON schema
            assert 'type' in tool.parameters
            assert tool.parameters['type'] == 'object'

    @pytest.mark.asyncio
    async def test_get_user_starred_repositories_tool_schema(self):
        """Test the schema of get_user_starred_repositories tool."""
        tools = await mcp.get_tools()
        starred_tool = next((t for t in tools if t.name == "get_user_starred_repositories"), None)
        
        assert starred_tool is not None
        assert "username" in starred_tool.parameters['properties']
        assert "cursor" in starred_tool.parameters['properties']
        
        # Username should be a string
        assert starred_tool.parameters['properties']['username']['type'] == 'string'
        # Cursor should be a string
        assert starred_tool.parameters['properties']['cursor']['type'] == 'string'

    @pytest.mark.asyncio
    async def test_get_repo_details_tool_schema(self):
        """Test the schema of get_repo_details tool."""
        tools = await mcp.get_tools()
        repo_tool = next((t for t in tools if t.name == "get_repo_details"), None)
        
        assert repo_tool is not None
        assert "repo_id" in repo_tool.parameters['properties']
        assert repo_tool.parameters['properties']['repo_id']['type'] == 'string'
        assert "repo_id" in repo_tool.parameters['required']

    @pytest.mark.asyncio
    async def test_get_batch_repo_details_tool_schema(self):
        """Test the schema of get_batch_repo_details tool."""
        tools = await mcp.get_tools()
        batch_tool = next((t for t in tools if t.name == "get_batch_repo_details"), None)
        
        assert batch_tool is not None
        assert "repo_ids" in batch_tool.parameters['properties']
        assert batch_tool.parameters['properties']['repo_ids']['type'] == 'array'
        assert "repo_ids" in batch_tool.parameters['required']

    @pytest.mark.asyncio
    async def test_create_full_analysis_bundle_tool_schema(self):
        """Test the schema of create_full_analysis_bundle tool."""
        tools = await mcp.get_tools()
        bundle_tool = next((t for t in tools if t.name == "create_full_analysis_bundle"), None)
        
        assert bundle_tool is not None
        assert "username" in bundle_tool.parameters['properties']
        assert bundle_tool.parameters['properties']['username']['type'] == 'string'


class TestMCPServerExecution:
    """Test MCP server tool execution."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client for testing."""
        client = AsyncMock()
        client.get_user_starred_repositories = AsyncMock()
        client.get_repository_readme = AsyncMock()
        client.get_multi_repository_readme = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_tool_execution_with_valid_parameters(self, mock_github_client):
        """Test tool execution with valid parameters."""
        with patch('github_stars_mcp.shared.github_client', mock_github_client):
            # Mock the GitHub API response
            mock_github_client.get_user_starred_repositories.return_value = {
                "edges": [],
                "totalCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # Execute the tool
            result = await mcp.call_tool(
                "get_user_starred_repositories",
                {"username": "testuser", "cursor": ""}
            )
            
            assert result is not None
            assert hasattr(result, 'repositories')
            assert hasattr(result, 'total_count')

    @pytest.mark.asyncio
    async def test_tool_execution_with_invalid_parameters(self):
        """Test tool execution with invalid parameters."""
        with pytest.raises(Exception):  # Should raise validation error
            await mcp.call_tool(
                "get_repo_details",
                {}  # Missing required repo_id parameter
            )

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, mock_github_client):
        """Test that tool execution properly handles errors."""
        with patch('github_stars_mcp.shared.github_client', mock_github_client):
            # Mock GitHub API to raise an error
            mock_github_client.get_user_starred_repositories.side_effect = Exception("API Error")
            
            with pytest.raises(Exception):
                await mcp.call_tool(
                    "get_user_starred_repositories",
                    {"username": "testuser"}
                )


class TestMCPServerResources:
    """Test MCP server resource functionality."""

    @pytest.mark.asyncio
    async def test_server_resources(self):
        """Test that server can list resources if any are defined."""
        resources = await mcp.get_resources()
        
        # Resources list should be accessible (may be empty)
        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_server_prompts(self):
        """Test that server can list prompts if any are defined."""
        prompts = await mcp.get_prompts()
        
        # Prompts list should be accessible (may be empty)
        assert isinstance(prompts, list)


class TestMCPServerConfiguration:
    """Test MCP server configuration and settings."""

    def test_server_name_configuration(self):
        """Test that server name is properly configured."""
        assert mcp.name == "GitHub Stars MCP Server"

    @pytest.mark.asyncio
    async def test_server_capabilities(self):
        """Test server capabilities."""
        # Server should support tools
        tools = await mcp.get_tools()
        assert len(tools) > 0
        
        # Test that server can handle tool calls
        assert hasattr(mcp, 'call_tool')

    def test_server_metadata(self):
        """Test server metadata and information."""
        # Server should have proper metadata
        assert hasattr(mcp, 'name')
        assert isinstance(mcp.name, str)
        assert len(mcp.name) > 0


class TestMCPServerIntegration:
    """Integration tests for MCP server."""

    @pytest.mark.asyncio
    async def test_full_server_workflow(self, mock_github_client):
        """Test complete server workflow with multiple tool calls."""
        with patch('github_stars_mcp.shared.github_client', mock_github_client):
            # Setup mocks
            mock_github_client.get_user_starred_repositories.return_value = {
                "edges": [
                    {
                        "starredAt": "2023-01-01T00:00:00Z",
                        "node": {
                            "id": "repo1",
                            "nameWithOwner": "user/repo",
                            "repositoryTopics": {"nodes": []},
                            "languages": {"edges": []}
                        }
                    }
                ],
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            mock_github_client.get_repository_readme.return_value = {
                "content": "# Test Repository"
            }
            
            # Step 1: Get starred repositories
            starred_result = await mcp.call_tool(
                "get_user_starred_repositories",
                {"username": "testuser"}
            )
            assert starred_result.total_count == 1
            
            # Step 2: Get repository details
            repo_result = await mcp.call_tool(
                "get_repo_details",
                {"repo_id": "user/repo"}
            )
            assert repo_result.readme_content == "# Test Repository"

    @pytest.mark.asyncio
    async def test_server_error_propagation(self, mock_github_client):
        """Test that server properly propagates errors from tools."""
        with patch('github_stars_mcp.shared.github_client', mock_github_client):
            # Mock an error in the GitHub client
            mock_github_client.get_user_starred_repositories.side_effect = Exception("GitHub API Error")
            
            # Error should be propagated
            with pytest.raises(Exception, match="GitHub API Error"):
                await mcp.call_tool(
                    "get_user_starred_repositories",
                    {"username": "testuser"}
                )

    @pytest.mark.asyncio
    async def test_server_concurrent_requests(self, mock_github_client):
        """Test server handling of concurrent requests."""
        import asyncio
        
        with patch('github_stars_mcp.shared.github_client', mock_github_client):
            mock_github_client.get_user_starred_repositories.return_value = {
                "edges": [],
                "totalCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": ""}
            }
            
            # Create multiple concurrent tool calls
            tasks = [
                mcp.call_tool("get_user_starred_repositories", {"username": f"user{i}"})
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert all(result.total_count == 0 for result in results)


class TestMCPServerValidation:
    """Test MCP server input validation."""

    @pytest.mark.asyncio
    async def test_parameter_validation(self):
        """Test that server validates tool parameters correctly."""
        # Test with missing required parameter
        with pytest.raises(Exception):
            await mcp.call_tool("get_repo_details", {})
        
        # Test with invalid parameter type
        with pytest.raises(Exception):
            await mcp.call_tool("get_batch_repo_details", {"repo_ids": "not_a_list"})

    @pytest.mark.asyncio
    async def test_tool_name_validation(self):
        """Test that server validates tool names."""
        with pytest.raises(Exception):
            await mcp.call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_parameter_type_validation(self, mock_github_client):
        """Test parameter type validation."""
        with patch('github_stars_mcp.shared.github_client', mock_github_client):
            # Test with correct types
            mock_github_client.get_multi_repository_readme.return_value = {}
            
            result = await mcp.call_tool(
                "get_batch_repo_details",
                {"repo_ids": ["user/repo1", "user/repo2"]}
            )
            assert result is not None
            
            # Test with incorrect types should raise validation error
            with pytest.raises(Exception):
                await mcp.call_tool(
                    "get_batch_repo_details",
                    {"repo_ids": 123}  # Should be array, not number
                )