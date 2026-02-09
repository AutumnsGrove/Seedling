"""RSS discovery module for Indeed job feeds."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

import feedparser
import httpx


@dataclass
class DiscoveredJob:
    """Represents a job discovered from RSS feed."""

    platform: str
    url: str
    title: str
    company: str | None
    location: str | None
    description: str
    published_at: str


class IndeedRSSDiscovery:
    """Discovers jobs from Indeed RSS feeds."""

    # Indeed RSS feed templates
    TECH_FEEDS = [
        "https://www.indeed.com/rss?q=cybersecurity+analyst&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=security+engineer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=systems+engineer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=platform+engineer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=full+stack+developer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=web+developer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=devops+engineer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=site+reliability+engineer&l=remote&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=cybersecurity+analyst&l=Atlanta%2C+GA&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=full+stack+developer&l=Atlanta%2C+GA&sort=date&fromage=3",
    ]

    SERVING_FEEDS = [
        "https://www.indeed.com/rss?q=server+restaurant&l=Atlanta%2C+GA&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=bartender&l=Atlanta%2C+GA&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=host+restaurant&l=Atlanta%2C+GA&sort=date&fromage=3",
        "https://www.indeed.com/rss?q=food+runner&l=Smyrna%2C+GA&sort=date&fromage=3",
    ]

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        """Initialize the RSS discovery module.

        Args:
            http_client: Optional httpx client for making requests.
        """
        self._client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                http2=True,
                headers={
                    "User-Agent": "Seedling/0.1 (job discovery)",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "IndeedRSSDiscovery":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def discover_from_feeds(
        self, feeds: list[str] | None = None
    ) -> AsyncIterator[DiscoveredJob]:
        """Discover jobs from RSS feeds.

        Args:
            feeds: Optional list of RSS feed URLs. Uses defaults if None.

        Yields:
            DiscoveredJob instances.
        """
        if feeds is None:
            feeds = self.TECH_FEEDS + self.SERVING_FEEDS

        client = await self._get_client()

        for feed_url in feeds:
            async for job in self._parse_feed(client, feed_url):
                yield job

    async def _parse_feed(
        self, client: httpx.AsyncClient, feed_url: str
    ) -> AsyncIterator[DiscoveredJob]:
        """Parse a single RSS feed.

        Args:
            client: HTTP client.
            feed_url: URL of the RSS feed.

        Yields:
            DiscoveredJob instances from the feed.
        """
        try:
            response = await client.get(feed_url)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.text)

            # Check for parsing errors
            if feed.bozo:
                # Malformed feed, skip
                return

            for entry in feed.entries:
                # Extract job info from entry
                job = self._entry_to_job(entry)
                if job is not None:
                    yield job

        except httpx.HTTPError as e:
            print(f"   ⚠️ Failed to fetch feed {feed_url}: {e}")
            return

    def _entry_to_job(
        self, entry: feedparser.FeedParserDict
    ) -> DiscoveredJob | None:
        """Convert a feed entry to a DiscoveredJob.

        Args:
            entry: Feed entry dict.

        Returns:
            DiscoveredJob or None if invalid.
        """
        # Get URL
        if not hasattr(entry, "link") or not entry.link:
            return None

        url = entry.link

        # Parse company from title (format: "Title at Company")
        title = getattr(entry, "title", "") or ""
        company = None

        if " at " in title:
            parts = title.rsplit(" at ", 1)
            title = parts[0].strip()
            company = parts[1].strip()

        # Extract location from description or tags
        location = None
        description = getattr(entry, "summary", "") or ""
        tags = getattr(entry, "tags", []) or []

        for tag in tags:
            if hasattr(tag, "term"):
                term = tag.term.lower()
                if "remote" in term or "hybrid" in term:
                    location = "Remote"
                elif "atlanta" in term or "ga" in term:
                    location = "Atlanta, GA"

        # Get published date
        published = getattr(entry, "published", "") or getattr(
            entry, "updated", ""
        )
        published_at = self._parse_date(published) if published else None

        return DiscoveredJob(
            platform="indeed",
            url=url,
            title=title,
            company=company,
            location=location,
            description=description[:500],  # Truncate for storage
            published_at=published_at,
        )

    def _parse_date(self, date_str: str) -> str:
        """Parse an RSS date string.

        Args:
            date_str: Date string from RSS.

        Returns:
            ISO format date string.
        """
        try:
            # Parse common RSS date formats
            parsed = feedparser._parse_date(date_str)
            if parsed is not None:
                return datetime(*parsed[:6]).isoformat()
        except Exception:
            pass

        # Fallback to current time
        return datetime.now().isoformat()


def generate_url_hash(url: str) -> str:
    """Generate a SHA-256 hash of a URL for deduplication.

    Args:
        url: The URL to hash.

    Returns:
        Hex string of the hash.
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


async def discover_jobs(
    http_client: httpx.AsyncClient | None = None,
) -> list[DiscoveredJob]:
    """Discover jobs from all configured RSS feeds.

    Args:
        http_client: Optional HTTP client.

    Returns:
        List of discovered jobs.
    """
    jobs: list[DiscoveredJob] = []

    async with IndeedRSSDiscovery(http_client) as discovery:
        async for job in discovery.discover_from_feeds():
            jobs.append(job)

    return jobs
