"""JSearch API integration for job discovery.

JSearch (by OpenWeb Ninja) provides job listings from Google for Jobs + major boards.
- Free tier: 200 requests/month
- Full job details including description, salary, requirements
- No bot protection issues - proper API access

Sign up: https://rapidapi.com/taq-najjar/api/jsearch
"""

import json
from dataclasses import dataclass
from typing import AsyncIterator

import httpx


@dataclass
class JSearchJob:
    """Represents a job from JSearch API."""

    job_id: str
    employer_name: str
    employer_website: str | None
    employer_company_type: str | None
    job_publisher: str
    job_employment_type: str
    job_title: str
    job_apply_link: str
    job_description: str
    job_is_remote: bool
    job_posted_at: str  # ISO datetime
    job_city: str | None
    job_state: str | None
    job_country: str
    job_latitude: float | None
    job_longitude: float | None
    job_min_salary: int | None
    job_max_salary: int | None
    job_salary_currency: str | None
    job_required_experience: dict | None
    job_required_skills: list[str] | None
    job_required_education: dict | None
    job_benefits: list[str] | None
    job_highlights: dict | None
    apply_options: list[dict] | None

    @property
    def platform(self) -> str:
        """Return normalized platform name."""
        publisher = self.job_publisher.lower()
        if "linkedin" in publisher:
            return "linkedin"
        elif "indeed" in publisher:
            return "indeed"
        elif "glassdoor" in publisher:
            return "glassdoor"
        elif "ziprecruiter" in publisher:
            return "ziprecruiter"
        elif "monster" in publisher:
            return "monster"
        else:
            return self.job_publisher.lower()

    @property
    def location(self) -> str | None:
        """Format location string."""
        parts = []
        if self.job_city:
            parts.append(self.job_city)
        if self.job_state:
            parts.append(self.job_state)
        if self.job_country and self.job_country != "US":
            parts.append(self.job_country)
        return ", ".join(parts) if parts else None


@dataclass
class JSearchResult:
    """Simplified result for Seedling pipeline."""

    url: str
    title: str
    company: str | None
    location: str | None
    description: str
    platform: str
    salary_min: int | None
    salary_max: int | None
    remote: bool
    posted_at: str


class JSearchDiscovery:
    """Discovers jobs using JSearch API."""

    TECH_QUERIES = [
        "cybersecurity analyst entry level remote",
        "security engineer junior remote",
        "full stack developer entry level Atlanta",
        "platform engineer remote junior",
        "devops engineer remote",
    ]

    SERVING_QUERIES = [
        "server bartender host restaurant Atlanta",
        "food service Atlanta hiring",
        "restaurant server Smyrna Georgia",
    ]

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize JSearch discovery.

        Args:
            api_key: RapidAPI key for JSearch.
            http_client: Optional HTTP client.
        """
        self.api_key = api_key
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

    async def __aenter__(self) -> "JSearchDiscovery":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def search(
        self,
        query: str,
        page: int = 1,
        num_pages: int = 1,
        date_posted: str = "week",
        remote_only: bool = True,
    ) -> AsyncIterator[JSearchJob]:
        """Search for jobs using JSearch API.

        Args:
            query: Search query string.
            page: Page number (1-100).
            num_pages: Number of pages to fetch (1-20).
            date_posted: Filter by date - "all", "today", "3days", "week", "month".
            remote_only: Only return remote-eligible jobs.

        Yields:
            JSearchJob instances.
        """
        if not self.api_key:
            return

        client = await self._get_client()

        try:
            response = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                headers={
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                    "X-RapidAPI-Key": self.api_key,
                },
                params={
                    "query": query,
                    "page": page,
                    "num_pages": num_pages,
                    "date_posted": date_posted,
                    "work_from_home": remote_only,
                    "employment_types": "FULLTIME,CONTRACTOR,PARTTIME",
                    "fields": ",".join([
                        "job_id",
                        "employer_name",
                        "employer_website",
                        "employer_company_type",
                        "job_publisher",
                        "job_employment_type",
                        "job_title",
                        "job_apply_link",
                        "job_description",
                        "job_is_remote",
                        "job_posted_at_datetime_utc",
                        "job_city",
                        "job_state",
                        "job_country",
                        "job_latitude",
                        "job_longitude",
                        "job_min_salary",
                        "job_max_salary",
                        "job_salary_currency",
                        "job_required_experience",
                        "job_required_skills",
                        "job_required_education",
                        "job_benefits",
                        "job_highlights",
                        "apply_options",
                    ]),
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "OK":
                print(f"   ⚠️ JSearch error: {data.get('error', {}).get('message', 'Unknown error')}")
                return

            results = data.get("data", [])

            for item in results:
                job = self._parse_job(item)
                if job:
                    yield job

        except httpx.HTTPError as e:
            print(f"   ⚠️ JSearch request failed: {e}")
            return

    def _parse_job(self, item: dict) -> JSearchJob | None:
        """Parse JSearch response item into JSearchJob.

        Args:
            item: Raw job data from API.

        Returns:
            JSearchJob instance or None if invalid.
        """
        job_id = item.get("job_id")
        if not job_id:
            return None

        return JSearchJob(
            job_id=job_id,
            employer_name=item.get("employer_name") or "Unknown",
            employer_website=item.get("employer_website"),
            employer_company_type=item.get("employer_company_type"),
            job_publisher=item.get("job_publisher", "Unknown"),
            job_employment_type=item.get("job_employment_type", "FULLTIME"),
            job_title=item.get("job_title", "Unknown Title"),
            job_apply_link=item.get("job_apply_link", ""),
            job_description=item.get("job_description", "") or "",
            job_is_remote=item.get("job_is_remote", False),
            job_posted_at=item.get("job_posted_at_datetime_utc", ""),
            job_city=item.get("job_city"),
            job_state=item.get("job_state"),
            job_country=item.get("job_country", "US"),
            job_latitude=item.get("job_latitude"),
            job_longitude=item.get("job_longitude"),
            job_min_salary=item.get("job_min_salary"),
            job_max_salary=item.get("job_max_salary"),
            job_salary_currency=item.get("job_salary_currency"),
            job_required_experience=item.get("job_required_experience"),
            job_required_skills=item.get("job_required_skills"),
            job_required_education=item.get("job_required_education"),
            job_benefits=item.get("job_benefits"),
            job_highlights=item.get("job_highlights"),
            apply_options=item.get("apply_options"),
        )

    def to_result(self, job: JSearchJob) -> JSearchResult:
        """Convert JSearchJob to simplified result.

        Args:
            job: Full JSearchJob.

        Returns:
            Simplified JSearchResult.
        """
        return JSearchResult(
            url=job.job_apply_link,
            title=job.job_title,
            company=job.employer_name,
            location=job.location,
            description=job.job_description[:1000] if job.job_description else "",
            platform=job.platform,
            salary_min=job.job_min_salary,
            salary_max=job.job_max_salary,
            remote=job.job_is_remote,
            posted_at=job.job_posted_at,
        )

    async def discover_from_queries(
        self,
        queries: list[str] | None = None,
        remote_only: bool = True,
    ) -> AsyncIterator[JSearchResult]:
        """Discover jobs from search queries.

        Args:
            queries: Optional list of queries. Uses defaults if None.
            remote_only: Only return remote-eligible jobs.

        Yields:
            JSearchResult instances.
        """
        if queries is None:
            queries = self.TECH_QUERIES + self.SERVING_QUERIES

        for query in queries:
            async for job in self.search(query, remote_only=remote_only):
                yield self.to_result(job)


async def discover_jobs(
    api_key: str,
    http_client: httpx.AsyncClient | None = None,
    remote_only: bool = True,
) -> list[JSearchResult]:
    """Discover jobs from JSearch API.

    Args:
        api_key: RapidAPI key for JSearch.
        http_client: Optional HTTP client.
        remote_only: Only return remote-eligible jobs.

    Returns:
        List of JSearchResult instances.
    """
    results: list[JSearchResult] = []

    async with JSearchDiscovery(
        api_key=api_key,
        http_client=http_client,
    ) as discovery:
        async for result in discovery.discover_from_queries(remote_only=remote_only):
            results.append(result)

    return results
