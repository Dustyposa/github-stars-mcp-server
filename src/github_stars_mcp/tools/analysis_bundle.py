"""High-level analysis bundle tool for GitHub starred repositories."""

from collections import Counter
from typing import Any

import structlog
from fastmcp import Context

from ..cache.decorators import multi_level_cache
from ..exceptions import GitHubAPIError
from ..models import (
    AnalysisBundle,
    BatchRepositoryDetailsResponse,
    StarredRepositoriesResponse,
)
from ..shared import mcp
from .batch_repo_details import get_batch_repo_details
from .starred_repo_list import get_user_starred_repositories

logger = structlog.get_logger(__name__)


def _generate_analysis_metadata(
    starred_response: StarredRepositoriesResponse,
    details_response: BatchRepositoryDetailsResponse
) -> dict[str, Any]:
    """Generate analysis metadata from repository data.

    Args:
        starred_response: Starred repositories response
        details_response: Batch repository details response

    Returns:
        Dictionary containing analysis metadata
    """
    # Language distribution
    languages = []
    topics = []
    star_counts = []

    for repo_detail in details_response.repository_details:
        repo = repo_detail.repository

        # Collect languages
        if repo.primary_language:
            languages.append(repo.primary_language)
        languages.extend(repo.languages)

        # Collect topics
        topics.extend(repo.repository_topics)

        # Collect star counts
        star_counts.append(repo.stargazer_count)

    # Calculate distributions
    language_distribution = dict(Counter(languages).most_common(10))
    topic_distribution = dict(Counter(topics).most_common(15))

    # Calculate statistics
    total_stars = sum(star_counts) if star_counts else 0
    avg_stars = total_stars / len(star_counts) if star_counts else 0

    return {
        "language_distribution": language_distribution,
        "topic_distribution": topic_distribution,
        "star_statistics": {
            "total_stars": total_stars,
            "average_stars": round(avg_stars, 2),
            "max_stars": max(star_counts) if star_counts else 0,
            "min_stars": min(star_counts) if star_counts else 0
        },
        "repository_counts": {
            "total_requested": starred_response.total_count,
            "successfully_detailed": details_response.success_count,
            "failed_details": details_response.error_count
        },
        "readme_statistics": {
            "with_readme": sum(1 for detail in details_response.repository_details if detail.has_readme),
            "without_readme": sum(1 for detail in details_response.repository_details if not detail.has_readme)
        }
    }


@mcp.tool
@multi_level_cache(ttl=1800, file_ttl=7200)  # 30 min L1, 2 hours L2
async def create_starred_repo_analysis_bundle(
    ctx: Context,
    username: str | None = None,
    include_readme: bool = True,
    max_repositories: int = 100,
    concurrent_requests: int = 10
) -> AnalysisBundle:
    """Create comprehensive analysis bundle for user starred repositories.

    This high-level tool combines multiple operations to generate a complete
    analysis of a user's starred repositories, including detailed information
    and statistical analysis.

    Args:
        username: GitHub username to analyze (optional, uses authenticated user if not provided)
        include_readme: Whether to include README content in repository details
        max_repositories: Maximum number of repositories to analyze (1-200, default: 100)
        concurrent_requests: Number of concurrent requests for batch operations (1-20, default: 10)

    Returns:
        AnalysisBundle containing complete repository analysis

    Raises:
        GitHubAPIError: If GitHub API requests fail
        ValueError: If parameters are invalid
    """
    # Validate parameters
    if max_repositories < 1 or max_repositories > 200:
        raise ValueError("max_repositories must be between 1 and 200")

    if concurrent_requests < 1 or concurrent_requests > 20:
        raise ValueError("concurrent_requests must be between 1 and 20")

    await ctx.info(
        "Starting starred repository analysis bundle creation",
        username=username or "authenticated_user",
        max_repositories=max_repositories,
        include_readme=include_readme
    )

    try:
        # Step 1: Get starred repositories list
        await ctx.info("Fetching starred repositories list")
        starred_data = await get_user_starred_repositories(
            ctx=ctx,
            username=username or "",
        )
        
        # Convert dict response to StarredRepositoriesResponse
        from ..models import StarredRepositoriesResponse, Repository
        repositories = []
        for repo_data in starred_data.get('repositories', []):
            repo = Repository(
                nameWithOwner=repo_data['full_name'],
                name=repo_data['name'],
                owner=repo_data['full_name'].split('/')[0],
                description=repo_data.get('description', ''),
                stargazerCount=repo_data['stars_count'],
                url=repo_data['url'],
                primaryLanguage=repo_data.get('language', ''),
                starredAt=repo_data.get('starred_at'),
                pushedAt=repo_data.get('updated_at'),
                diskUsage=0,
                repositoryTopics=repo_data.get('topics', []),
                languages=[repo_data.get('language', '')] if repo_data.get('language') else []
            )
            repositories.append(repo)
        
        starred_response = StarredRepositoriesResponse(
            repositories=repositories,
            total_count=starred_data.get('total_count', len(repositories)),
            has_more=starred_data.get('has_next_page', False),
            next_cursor=starred_data.get('end_cursor', '')
        )

        if not starred_response.repositories:
            await ctx.info("No starred repositories found")
            from datetime import datetime
            return AnalysisBundle(
                username=username or "authenticated_user",
                total_repositories=0,
                repositories=[],
                language_distribution=[],
                topic_distribution=[],
                star_statistics={
                    "total_stars": 0,
                    "average_stars": 0.0,
                    "median_stars": 0.0,
                    "max_stars": 0,
                    "min_stars": 0
                },
                analysis_timestamp=datetime.utcnow(),
                processing_summary={
                    "total_requested": 0,
                    "successfully_detailed": 0,
                    "failed_details": 0,
                    "readme_statistics": {"with_readme": 0, "without_readme": 0}
                }
            )

        # Step 2: Extract repository names for batch details
        repository_names = [repo.name_with_owner for repo in starred_response.repositories]

        await ctx.info(
            "Fetching detailed repository information",
            repository_count=len(repository_names)
        )

        # Step 3: Get batch repository details
        details_response = await get_batch_repo_details(
            ctx=ctx,
            repository_names=repository_names,
            max_concurrent=concurrent_requests
        )

        # Step 4: Generate analysis data
        await ctx.info("Generating analysis data")
        
        # Collect languages and topics
        languages = []
        topics = []
        star_counts = []
        
        for repo_detail in details_response.repository_details:
            repo = repo_detail.repository
            
            # Collect languages
            if repo.primary_language:
                languages.append(repo.primary_language)
            languages.extend(repo.languages)
            
            # Collect topics
            topics.extend(repo.repository_topics)
            
            # Collect star counts
            star_counts.append(repo.stargazer_count)
        
        # Calculate distributions
        from ..models import LanguageStats, TopicStats, StarStats
        from collections import Counter
        import statistics
        
        language_counter = Counter(languages)
        topic_counter = Counter(topics)
        
        language_distribution = [
            LanguageStats(
                language=lang,
                count=count,
                percentage=round(count / len(details_response.repository_details) * 100, 2)
            )
            for lang, count in language_counter.most_common(10)
        ]
        
        topic_distribution = [
            TopicStats(
                topic=topic,
                count=count,
                percentage=round(count / len(details_response.repository_details) * 100, 2)
            )
            for topic, count in topic_counter.most_common(15)
        ]
        
        # Calculate star statistics
        total_stars = sum(star_counts) if star_counts else 0
        avg_stars = statistics.mean(star_counts) if star_counts else 0.0
        median_stars = statistics.median(star_counts) if star_counts else 0.0
        
        star_statistics = StarStats(
            total_stars=total_stars,
            average_stars=round(avg_stars, 2),
            median_stars=round(median_stars, 2),
            max_stars=max(star_counts) if star_counts else 0,
            min_stars=min(star_counts) if star_counts else 0
        )
        
        # Processing summary
        processing_summary = {
            "total_requested": starred_response.total_count,
            "successfully_detailed": details_response.success_count,
            "failed_details": details_response.error_count,
            "readme_statistics": {
                "with_readme": sum(1 for detail in details_response.repository_details if detail.has_readme),
                "without_readme": sum(1 for detail in details_response.repository_details if not detail.has_readme)
            }
        }
        
        # Step 5: Create analysis bundle
        from datetime import datetime
        bundle = AnalysisBundle(
            username=username or "authenticated_user",
            total_repositories=len(details_response.repository_details),
            repositories=details_response.repository_details,
            language_distribution=language_distribution,
            topic_distribution=topic_distribution,
            star_statistics=star_statistics,
            analysis_timestamp=datetime.utcnow(),
            processing_summary=processing_summary
        )

        await ctx.info(
            "Analysis bundle created successfully",
            total_starred=starred_response.total_count,
            detailed_repos=details_response.success_count,
            failed_repos=details_response.error_count,
            top_languages=[lang.language for lang in language_distribution[:5]]
        )

        return bundle

    except GitHubAPIError:
        raise
    except Exception as e:
        await ctx.error(
            "Failed to create analysis bundle",
            username=username,
            error=str(e)
        )
        raise GitHubAPIError(f"Failed to create analysis bundle: {str(e)}")


# get_analysis_bundle_summary tool removed - summary data is available in AnalysisBundle.summary_stats property
