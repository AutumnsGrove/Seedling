"""Web search discovery module using Tavily (primary) or Exa (fallback).

Tavily handles both search and content crawling in one API call.
"""

import json
from dataclasses import dataclass
from typing import AsyncIterator

import httpx


@dataclass
class SearchResult:
    """Represents a job from web search."""

    url: str
    title: str
    snippet: str
    source: str  # "tavily" or "exa"


@dataclass
class CrawledJob:
    """Represents a job with full content from Tavily crawl."""

    url: str
    title: str
    content: str
    source: str = "tavily"


class WebSearchDiscovery:
    """Discovers jobs using Tavily (primary) or Exa (fallback)."""

    TECH_QUERIES = [
        "cybersecurity analyst entry level remote job posting 2025",
        "security engineer junior remote job",
        "full stack developer entry level Atlanta",
        "platform engineer remote junior",
        "devops engineer remote job posting",
    ]

    SERVING_QUERIES = [
        "server bartender host restaurant Atlanta 2025",
        "food service Atlanta hiring",
        "restaurant hiring Smyrna Georgia server",
    ]

    def __init__(
        self,
        tavily_api_key: str | None = None,
        exa_api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the web search discovery module.

        Args:
            tavily_api_key: Tavily API key (preferred).
            exa_api_key: Exa API key (fallback).
            http_client: Optional HTTP client.
        """
        self.tavily_api_key = tavily_api_key
        self.exa_api_key = exa_api_key
        self._client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0, http2=True)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "WebSearchDiscovery":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def search_tavily(
        self, query: str, num_results: int = 10
    ) -> AsyncIterator[SearchResult]:
        """Search using Tavily API.

        Args:
            query: Search query.
            num_results: Number of results to return.

        Yields:
            SearchResult instances.
        """
        if not self.tavily_api_key:
            return

        client = await self._get_client()

        try:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "api_key": self.tavily_api_key,
                    "max_results": num_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            for result in results:
                yield SearchResult(
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    snippet=result.get("content", ""),
                    source="tavily",
                )

        except httpx.HTTPError as e:
            print(f"   ⚠️ Tavily search failed: {e}")
            return

    async def crawl_tavily(
        self, urls: list[str], query: str = "Extract job details including title, company, location, salary, and full description"
    ) -> AsyncIterator[CrawledJob]:
        """Extract content from specific URLs using Tavily's extract endpoint.

        Args:
            urls: List of URLs to extract content from.
            query: Extraction query for what to extract from pages.

        Yields:
            CrawledJob instances with full content.
        """
        if not self.tavily_api_key or not urls:
            return

        client = await self.get_client()

        # Ensure API key has tvly- prefix for Authorization header
        api_key = self.tavily_api_key
        if not api_key.startswith("tvly-"):
            api_key = f"tvly-{api_key}"

        try:
            response = await client.post(
                "https://api.tavily.com/extract",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "urls": urls,
                    "query": query,
                    "extract_depth": "basic",
                    "format": "markdown",
                },
                timeout=60.0,
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            failed = {f["url"]: f.get("error", "Unknown error") for f in data.get("failed_results", [])}

            for result in results:
                url = result.get("url", "")
                content = result.get("raw_content", result.get("content", ""))
                title = result.get("title", "")

                yield CrawledJob(
                    url=url,
                    title=title,
                    content=content,
                    source="tavily",
                )

            # Log failed URLs
            for url, error in failed.items():
                print(f"   ⚠️ Tavily extract failed for {url}: {error}")

        except httpx.HTTPError as e:
            print(f"   ⚠️ Tavily extract failed: {e}")
            return

    async def search_exa(
        self, query: str, num_results: int = 10
    ) -> AsyncIterator[SearchResult]:
        """Search using Exa API (fallback).

        Args:
            query: Search query.
            num_results: Number of results to return.

        Yields:
            SearchResult instances.
        """
        if not self.exa_api_key:
            return

        client = await self._get_client()

        try:
            response = await client.post(
                "https://api.exa.com/search",
                headers={"Authorization": f"Bearer {self.exa_api_key}"},
                json={
                    "query": query,
                    "numResults": num_results,
                    "type": "auto",
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            for result in results:
                yield SearchResult(
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    source="exa",
                )

        except httpx.HTTPError as e:
            print(f"   ⚠️ Exa search failed: {e}")
            return

    async def discover_from_queries(
        self,
        queries: list[str] | None = None,
        provider: str = "tavily",
    ) -> AsyncIterator[SearchResult]:
        """Discover jobs from search queries.

        Args:
            queries: Optional list of queries. Uses defaults if None.
            provider: Search provider ("tavily" or "exa").

        Yields:
            SearchResult instances.
        """
        if queries is None:
            queries = self.TECH_QUERIES + self.SERVING_QUERIES

        for query in queries:
            if provider == "tavily":
                async for result in self.search_tavily(query):
                    yield result
            else:
                async for result in self.search_exa(query):
                    yield result

    async def get_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        return await self._get_client()


async def discover_jobs(
    tavily_api_key: str | None = None,
    exa_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    provider: str = "tavily",
) -> list[SearchResult]:
    """Discover jobs from web searches.

    Args:
        tavily_api_key: Tavily API key (preferred).
        exa_api_key: Exa API key (fallback).
        http_client: Optional HTTP client.
        provider: Search provider to use ("tavily" or "exa").

    Returns:
        List of search results.
    """
    results: list[SearchResult] = []

    async with WebSearchDiscovery(
        tavily_api_key=tavily_api_key,
        exa_api_key=exa_api_key,
        http_client=http_client,
    ) as discovery:
        async for result in discovery.discover_from_queries(provider=provider):
            results.append(result)

    return results


async def crawl_jobs(
    urls: list[str],
    tavily_api_key: str | None = None,
    query: str = "Extract job details: title, company, location, salary range, job description, requirements, and application method",
) -> list[CrawledJob]:
    """Crawl job pages to extract full content.

    Args:
        urls: List of URLs to crawl.
        tavily_api_key: Tavily API key.
        query: Extraction query.

    Returns:
        List of CrawledJob instances.
    """
    if not tavily_api_key:
        return []

    results: list[CrawledJob] = []

    async with WebSearchDiscovery(
        tavily_api_key=tavily_api_key,
    ) as discovery:
        async for result in discovery.crawl_tavily(urls, query):
            results.append(result)

    return results
