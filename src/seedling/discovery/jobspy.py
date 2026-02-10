"""Job discovery using python-jobspy.

Wraps the JobSpy library to discover jobs from Indeed, Google Jobs, and other sources.
JobSpy is synchronous, so we wrap in asyncio.to_thread() for async compatibility.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional

from jobspy import scrape_jobs

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredJob:
    """Represents a job discovered from any source."""

    platform: str
    url: str
    title: str
    company: str | None
    location: str | None
    description: str
    published_at: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    is_remote: bool = False
    site: str | None = None


def generate_url_hash(url: str) -> str:
    """Generate a SHA-256 hash of a URL for deduplication.

    Args:
        url: The URL to hash.

    Returns:
        Hex string of the hash.
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


@dataclass
class SearchConfig:
    """Configuration for a single job search."""

    query: str
    location: str
    category: str  # "tech" or "serving"
    site_name: list[str] = field(default_factory=lambda: ["indeed", "google"])
    results_wanted: int = 25
    hours_old: int = 72
    is_remote: bool = False


# Default search configurations
TECH_SEARCHES = [
    SearchConfig(
        query="cybersecurity analyst",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="security engineer",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="full stack developer",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="full stack developer",
        location="Atlanta, GA",
        category="tech",
    ),
    SearchConfig(
        query="devops engineer",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="site reliability engineer",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="platform engineer",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="web developer",
        location="",
        category="tech",
        is_remote=True,
    ),
    SearchConfig(
        query="cybersecurity analyst",
        location="Atlanta, GA",
        category="tech",
    ),
]

SERVING_SEARCHES = [
    SearchConfig(
        query="restaurant server",
        location="Atlanta, GA",
        category="serving",
        site_name=["indeed", "google"],
    ),
    SearchConfig(
        query="bartender",
        location="Atlanta, GA",
        category="serving",
        site_name=["indeed", "google"],
    ),
    SearchConfig(
        query="host restaurant",
        location="Atlanta, GA",
        category="serving",
        site_name=["indeed", "google"],
    ),
    SearchConfig(
        query="restaurant server",
        location="Smyrna, GA",
        category="serving",
        site_name=["indeed", "google"],
    ),
]


class JobSpyDiscovery:
    """Discovers jobs using python-jobspy."""

    def __init__(
        self,
        tech_searches: list[SearchConfig] | None = None,
        serving_searches: list[SearchConfig] | None = None,
    ) -> None:
        """Initialize JobSpy discovery.

        Args:
            tech_searches: Custom tech search configs. Uses defaults if None.
            serving_searches: Custom serving search configs. Uses defaults if None.
        """
        self.tech_searches = tech_searches if tech_searches is not None else TECH_SEARCHES
        self.serving_searches = serving_searches if serving_searches is not None else SERVING_SEARCHES

    def _run_search(self, config: SearchConfig) -> list[DiscoveredJob]:
        """Run a single search and return discovered jobs.

        Args:
            config: Search configuration.

        Returns:
            List of discovered jobs.
        """
        try:
            kwargs = {
                "site_name": config.site_name,
                "search_term": config.query,
                "results_wanted": config.results_wanted,
                "hours_old": config.hours_old,
                "country_indeed": "USA",
            }

            if config.location:
                kwargs["location"] = config.location

            if config.is_remote:
                kwargs["is_remote"] = True

            df = scrape_jobs(**kwargs)

            if df is None or df.empty:
                return []

            jobs = []
            for _, row in df.iterrows():
                job_url = str(row.get("job_url", ""))
                if not job_url or job_url == "nan":
                    continue

                title = str(row.get("title", "")) if row.get("title") is not None else ""
                if not title or title == "nan":
                    continue

                company = str(row.get("company", "")) if row.get("company") is not None else None
                if company == "nan":
                    company = None

                location = str(row.get("location", "")) if row.get("location") is not None else None
                if location == "nan":
                    location = None

                description = str(row.get("description", "")) if row.get("description") is not None else ""
                if description == "nan":
                    description = ""

                is_remote = bool(row.get("is_remote", False))

                # Parse salary
                salary_min = None
                salary_max = None
                min_amount = row.get("min_amount")
                max_amount = row.get("max_amount")
                if min_amount is not None and str(min_amount) != "nan":
                    try:
                        salary_min = int(float(min_amount))
                    except (ValueError, TypeError):
                        pass
                if max_amount is not None and str(max_amount) != "nan":
                    try:
                        salary_max = int(float(max_amount))
                    except (ValueError, TypeError):
                        pass

                # Parse date
                date_posted = row.get("date_posted")
                published_at = None
                if date_posted is not None and str(date_posted) != "nan":
                    published_at = str(date_posted)

                site = str(row.get("site", "")) if row.get("site") is not None else None
                if site == "nan":
                    site = None

                jobs.append(DiscoveredJob(
                    platform=site or "jobspy",
                    url=job_url,
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    published_at=published_at,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    is_remote=is_remote,
                    site=site,
                ))

            return jobs

        except Exception as e:
            logger.warning(f"Search failed for '{config.query}' in '{config.location}': {e}")
            return []

    def discover_all_sync(self) -> list[DiscoveredJob]:
        """Run all searches synchronously and return deduplicated results.

        Returns:
            List of unique discovered jobs.
        """
        all_jobs: list[DiscoveredJob] = []
        seen_hashes: set[str] = set()

        all_searches = self.tech_searches + self.serving_searches

        for config in all_searches:
            logger.info(f"Searching: '{config.query}' in '{config.location or 'remote'}'")
            jobs = self._run_search(config)

            for job in jobs:
                url_hash = generate_url_hash(job.url)
                if url_hash not in seen_hashes:
                    seen_hashes.add(url_hash)
                    all_jobs.append(job)

            logger.info(f"  Found {len(jobs)} jobs ({len(all_jobs)} total unique)")

        return all_jobs

    async def discover_all_async(self) -> list[DiscoveredJob]:
        """Run all searches asynchronously via thread pool.

        Returns:
            List of unique discovered jobs.
        """
        return await asyncio.to_thread(self.discover_all_sync)
