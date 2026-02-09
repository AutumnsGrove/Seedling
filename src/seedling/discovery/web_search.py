"""Web search discovery module using Exa or Tavily API."""

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
    source: str  # "exa" or "tavily"


class WebSearchDiscovery:
    """Discovers jobs using web search APIs (Exa or Tavily)."""

    # Default search queries
    TECH_QUERIES = [
        "cybersecurity analyst entry level remote job posting site:linkedin.com/jobs",
        "security engineer junior remote site:dice.com",
        "full stack developer entry level Atlanta site:glassdoor.com/job-listing",
    ]

    SERVING_QUERIES = [
        "server bartender host Atlanta site:poached.com",
        "restaurant server Atlanta site:culinaryagents.com",
    ]

    def __init__(
        self,
        exa_api_key: str | None = None,
        tavily_api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the web search discovery module.

        Args:
            exa_api_key: Exa API key (optional).
            tavily_api_key: Tavily API key (optional).
            http_client: Optional HTTP client.
        """
        self.exa_api_key = exa_api_key
        self.tavily_api_key = tavily_api_key
        self._client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, http2=True)
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

    async def search_exa(
        self, query: str, num_results: int = 10
    ) -> AsyncIterator[SearchResult]:
        """Search using Exa API.

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
                params={"api_key": self.tavily_api_key},
                json={
                    "query": query,
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

    async def discover_from_queries(
        self,
        queries: list[str] | None = None,
        provider: str = "exa",
    ) -> AsyncIterator[SearchResult]:
        """Discover jobs from search queries.

        Args:
            queries: Optional list of queries. Uses defaults if None.
            provider: Search provider ("exa" or "tavily").

        Yields:
            SearchResult instances.
        """
        if queries is None:
            queries = self.TECH_QUERIES + self.SERVING_QUERIES

        for query in queries:
            if provider == "exa":
                async for result in self.search_exa(query):
                    yield result
            else:
                async for result in self.search_tavily(query):
                    yield result


async def discover_jobs(
    exa_api_key: str | None = None,
    tavily_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    provider: str = "exa",
) -> list[SearchResult]:
    """Discover jobs from web searches.

    Args:
        exa_api_key: Exa API key.
        tavily_api_key: Tavily API key.
        http_client: Optional HTTP client.
        provider: Search provider to use.

    Returns:
        List of search results.
    """
    results: list[SearchResult] = []

    async with WebSearchDiscovery(
        exa_api_key=exa_api_key,
        tavily_api_key=tavily_api_key,
        http_client=http_client,
    ) as discovery:
        async for result in discovery.discover_from_queries(provider=provider):
            results.append(result)

    return results
