"""Job discovery module.

Discovers job listings from:
- Indeed RSS feeds
- Web search (Exa/Tavily)
- Playwright (backup for JS-rendered pages)
"""

from seedling.discovery.rss import (
    DiscoveredJob,
    IndeedRSSDiscovery,
    discover_jobs as discover_jobs_from_rss,
    generate_url_hash,
)
from seedling.discovery.web_search import (
    SearchResult,
    WebSearchDiscovery,
    discover_jobs as discover_jobs_from_web,
)
from seedling.discovery.playwright import (
    PlaywrightDiscovery,
    PlaywrightJob,
    scrape_job_page,
)

__all__ = [
    # RSS
    "DiscoveredJob",
    "IndeedRSSDiscovery",
    "discover_jobs_from_rss",
    "generate_url_hash",
    # Web Search
    "SearchResult",
    "WebSearchDiscovery",
    "discover_jobs_from_web",
    # Playwright
    "PlaywrightDiscovery",
    "PlaywrightJob",
    "scrape_job_page",
]
