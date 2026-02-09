"""Tests for the discovery module."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from seedling.discovery import DiscoveredJob, generate_url_hash
from seedling.discovery.rss import IndeedRSSDiscovery


class TestGenerateUrlHash:
    """Tests for URL hash generation."""

    def test_generate_url_hash_consistency(self) -> None:
        """Same URL should produce same hash."""
        url = "https://www.indeed.com/viewjob?jk=abc123"
        hash1 = generate_url_hash(url)
        hash2 = generate_url_hash(url)
        assert hash1 == hash2

    def test_generate_url_hash_different_urls(self) -> None:
        """Different URLs should produce different hashes."""
        url1 = "https://www.indeed.com/viewjob?jk=abc123"
        url2 = "https://www.indeed.com/viewjob?jk=def456"
        hash1 = generate_url_hash(url1)
        hash2 = generate_url_hash(url2)
        assert hash1 != hash2

    def test_generate_url_hash_format(self) -> None:
        """Hash should be valid hex string."""
        url = "https://www.indeed.com/viewjob?jk=abc123"
        hash_str = generate_url_hash(url)
        assert len(hash_str) == 64  # SHA-256 produces 64 hex chars
        assert all(c in "0123456789abcdef" for c in hash_str)


class TestIndeedRSSDiscovery:
    """Tests for Indeed RSS discovery."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock HTTP client."""
        client = MagicMock()
        client.get = AsyncMock()
        return client

    @pytest.fixture
    def discovery(self, mock_client: MagicMock) -> IndeedRSSDiscovery:
        """Create a discovery instance with mock client."""
        return IndeedRSSDiscovery(http_client=mock_client)

    @pytest.mark.asyncio
    async def test_parse_feed_empty(self, discovery: IndeedRSSDiscovery, mock_client: MagicMock) -> None:
        """Test parsing an empty feed."""
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
            </channel>
        </rss>
        """
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            discovery, "_get_client", return_value=mock_client
        ):
            mock_client.get = AsyncMock(return_value=mock_response)

            jobs = []
            async for job in discovery._parse_feed(
                mock_client, "https://example.com/rss"
            ):
                jobs.append(job)

            assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_parse_feed_with_entry(self, discovery: IndeedRSSDiscovery, mock_client: MagicMock) -> None:
        """Test parsing a feed with entries."""
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Software Engineer at Acme Corp</title>
                    <link>https://www.indeed.com/viewjob?jk=abc123</link>
                    <description>Full description here</description>
                    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """
        mock_response.raise_for_status = MagicMock()

        with patch.object(discovery, "_get_client"):
            mock_client.get = AsyncMock(return_value=mock_response)

            jobs = []
            async for job in discovery._parse_feed(
                mock_client, "https://example.com/rss"
            ):
                jobs.append(job)

            assert len(jobs) == 1
            assert jobs[0].title == "Software Engineer"
            assert jobs[0].company == "Acme Corp"
            assert jobs[0].platform == "indeed"

    def test_entry_to_job_with_company(self, discovery: IndeedRSSDiscovery) -> None:
        """Test extracting job with company in title."""
        entry = MagicMock()
        entry.link = "https://www.indeed.com/viewjob?jk=abc123"
        entry.title = "Software Engineer at Acme Corp"
        entry.summary = "Job description"
        entry.published = "Mon, 01 Jan 2024 00:00:00 GMT"
        entry.tags = []

        job = discovery._entry_to_job(entry)

        assert job is not None
        assert job.title == "Software Engineer"
        assert job.company == "Acme Corp"
        assert job.url == "https://www.indeed.com/viewjob?jk=abc123"

    def test_entry_to_job_without_company(self, discovery: IndeedRSSDiscovery) -> None:
        """Test extracting job without company in title."""
        entry = MagicMock()
        entry.link = "https://www.indeed.com/viewjob?jk=abc123"
        entry.title = "Software Engineer"
        entry.summary = "Job description"
        entry.published = ""
        entry.tags = []

        job = discovery._entry_to_job(entry)

        assert job is not None
        assert job.title == "Software Engineer"
        assert job.company is None

    def test_entry_to_job_missing_link(self, discovery: IndeedRSSDiscovery) -> None:
        """Test entry with no link returns None."""
        entry = MagicMock()
        entry.link = None
        entry.title = "Software Engineer"
        entry.summary = ""
        entry.published = ""
        entry.tags = []

        job = discovery._entry_to_job(entry)

        assert job is None


class TestDiscoveredJob:
    """Tests for DiscoveredJob dataclass."""

    def test_discovered_job_creation(self) -> None:
        """Test creating a DiscoveredJob."""
        job = DiscoveredJob(
            platform="indeed",
            url="https://www.indeed.com/viewjob?jk=abc123",
            title="Software Engineer",
            company="Acme Corp",
            location="Remote",
            description="Full job description",
            published_at="2024-01-01T00:00:00",
        )

        assert job.platform == "indeed"
        assert job.url == "https://www.indeed.com/viewjob?jk=abc123"
        assert job.title == "Software Engineer"
        assert job.company == "Acme Corp"
        assert job.location == "Remote"
