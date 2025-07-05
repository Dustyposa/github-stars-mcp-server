# GitHub Stars MCP Server

A high-performance Model Context Protocol (MCP) server for GitHub stars analysis and timeline tracking.

## Overview

This MCP server provides tools for analyzing GitHub user starred repositories, offering insights into development trends, technology adoption patterns, and timeline analysis.

## Features

- **GitHub Stars Analysis**: Retrieve and analyze user starred repositories
- **Timeline Tracking**: Track starring patterns over time
- **Technology Insights**: Analyze technology trends from starred repositories
- **High Performance**: Built with async/await patterns and Redis caching
- **GitHub App Authentication**: Secure authentication using GitHub Apps

## Technology Stack

- **Python 3.11+**: Modern Python with type hints
- **FastMCP 2.2.0+**: High-performance MCP framework
- **Pydantic 2.0+**: Data validation and serialization
- **httpx**: Async HTTP client for GitHub API
- **Redis 5.0+**: Caching and performance optimization
- **GitHub GraphQL API**: Efficient data retrieval
- **structlog**: Structured logging

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/github-stars-mcp-server.git
cd github-stars-mcp-server

# Install dependencies using uv
uv sync

# Activate virtual environment
source .venv/bin/activate
```

## Configuration

Create a `.env` file with your GitHub App credentials:

```env
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY_PATH=path/to/private-key.pem
GITHUB_APP_INSTALLATION_ID=your_installation_id
REDIS_URL=redis://localhost:6379
```

## Usage

```bash
# Start the MCP server
github-stars-mcp-server
```

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy src/
```

## Docker

```bash
# Build Docker image
docker build -t github-stars-mcp-server .

# Run container
docker run -p 8000:8000 --env-file .env github-stars-mcp-server
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Architecture

This server follows a modular architecture:

- `src/github_stars_mcp_server/config.py`: Configuration management
- `src/github_stars_mcp_server/models.py`: Pydantic data models
- `src/github_stars_mcp_server/github_client.py`: GitHub API client
- `src/github_stars_mcp_server/server.py`: MCP server implementation
- `src/github_stars_mcp_server/tools/`: MCP tools implementation

## Performance

- Async/await throughout for non-blocking operations
- Redis caching for frequently accessed data
- GraphQL for efficient API queries
- Connection pooling for optimal resource usage

## Security

- GitHub App authentication for secure API access
- Environment-based configuration
- Input validation with Pydantic
- Structured logging for audit trails