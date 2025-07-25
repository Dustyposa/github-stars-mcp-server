# GitHub Stars MCP Server

一个高性能的 MCP (Model Context Protocol) 服务器，用于 GitHub 星标仓库分析和时间线跟踪。

## 功能特性

- 🌟 **星标仓库管理**: 获取和分析用户的 GitHub 星标仓库
- 📊 **数据分析**: 提供语言分布、主题统计、星标趋势等分析
- 🚀 **批量处理**: 支持批量获取仓库详情和 README 内容
- 💾 **多级缓存**: L1 (内存) + L2 (Redis) 缓存系统提升性能
- 🔧 **精简工具集**: 4个核心工具，专注于核心功能

## 安装

1. 克隆仓库:
```bash
git clone <repository-url>
cd github-stars-mcp-server
```

2. 安装依赖:
```bash
pip install -e .
```

3. 配置环境变量:
```bash
export GITHUB_TOKEN="your_github_token_here"
export REDIS_URL="redis://localhost:6379/0"  # 可选
```

## 使用方法

### 启动服务器

```bash
python -m github_stars_mcp.server
```

### 可用工具

#### 1. 获取星标仓库列表
```python
get_user_starred_repositories(
    username="",  # 空字符串表示当前认证用户
    limit=50,     # 返回数量限制 (1-100)
    cursor=""     # 分页游标
)
```

#### 2. 获取单个仓库详情
```python
get_repo_details(
    repository_name="owner/repo"  # 仓库名称格式: owner/repo
)
```

#### 3. 批量获取仓库详情
```python
get_batch_repo_details(
    repository_names=["owner/repo1", "owner/repo2"],
    max_concurrent=10  # 最大并发请求数 (1-20)
)
```

#### 4. 创建综合分析报告
```python
create_starred_repo_analysis_bundle(
    username="",           # GitHub 用户名 (可选)
    include_readme=True,   # 是否包含 README 内容
    max_repositories=100,  # 最大分析仓库数 (1-200)
    concurrent_requests=10 # 并发请求数 (1-20)
)
```

## 配置选项

### 环境变量

- `GITHUB_TOKEN`: GitHub Personal Access Token (必需)
- `REDIS_URL`: Redis 连接 URL (可选，默认: redis://localhost:6379/0)
- `LOG_LEVEL`: 日志级别 (可选，默认: INFO)
- `DANGEROUSLY_OMIT_AUTH`: 是否跳过认证检查 (可选，默认: true)

### 缓存配置

- **L1 缓存**: 内存中的 TTL 缓存，默认 128 个条目，5 分钟过期
- **L2 缓存**: Redis 缓存，用于持久化和跨实例共享

## 数据模型

### StarredRepository
包含星标仓库的完整信息，包括:
- 基本信息 (名称、描述、URL)
- 统计数据 (星标数、分叉数)
- 元数据 (创建时间、更新时间、星标时间)
- 标签和主题

### AnalysisBundle
综合分析报告，包含:
- 语言分布统计
- 主题分布统计
- 星标数量统计
- 处理摘要和元数据

## 错误处理

服务器包含完善的错误处理机制:
- `AuthenticationError`: GitHub 认证失败
- `RateLimitError`: API 速率限制
- `GitHubAPIError`: GitHub API 错误
- `CacheError`: 缓存操作错误
- `ConfigurationError`: 配置错误

## 性能优化

- 多级缓存系统减少 API 调用
- 并发控制避免速率限制
- 分页支持处理大量数据
- 异步操作提升响应速度

## 开发

### 运行测试
```bash
pytest
```

### 代码检查
```bash
ruff check src/
mypy src/
```

### 格式化代码
```bash
ruff format src/
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！