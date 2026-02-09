"""Tests for the notification module."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from seedling.notify.digest import (
    DigestEmailBuilder,
    DigestJob,
    DigestStats,
    ZephyrClient,
    create_digest_jobs_from_db_jobs,
    send_digest,
)


class TestDigestJob:
    """Tests for the DigestJob dataclass."""

    def test_digest_job_creation(self) -> None:
        """Test creating a DigestJob."""
        job = DigestJob(
            id="job-123",
            title="Software Engineer",
            company="Acme Corp",
            location="Remote",
            match_score=85,
            score_summary="Great match for your skills",
            category="tech-devops",
            url="https://example.com/job",
            resume_url="https://r2.dev/resume.pdf",
            cover_letter_url="https://r2.dev/cover.pdf",
            cover_letter_requested=True,
        )

        assert job.id == "job-123"
        assert job.title == "Software Engineer"
        assert job.match_score == 85
        assert job.category == "tech-devops"
        assert job.cover_letter_requested is True

    def test_digest_job_optional_fields(self) -> None:
        """Test DigestJob with minimal fields."""
        job = DigestJob(
            id="job-456",
            title="Server",
            company=None,
            location=None,
            match_score=70,
            score_summary="Good serving position",
            category="serving",
            url="https://example.com/job",
            resume_url=None,
            cover_letter_url=None,
            cover_letter_requested=False,
        )

        assert job.company is None
        assert job.resume_url is None


class TestDigestStats:
    """Tests for the DigestStats dataclass."""

    def test_digest_stats_creation(self) -> None:
        """Test creating DigestStats."""
        stats = DigestStats(
            total_discovered=10,
            total_extracted=8,
            total_rejected=2,
            total_qualified=6,
            tech_count=4,
            serving_count=2,
        )

        assert stats.total_discovered == 10
        assert stats.total_qualified == 6
        assert stats.tech_count == 4


class TestDigestEmailBuilder:
    """Tests for the DigestEmailBuilder class."""

    @pytest.fixture
    def templates_dir(self) -> Path:
        """Get the templates directory."""
        return Path(__file__).parent.parent / "templates"

    @pytest.fixture
    def builder(self, templates_dir: Path) -> DigestEmailBuilder:
        """Create a DigestEmailBuilder instance."""
        return DigestEmailBuilder(templates_dir=templates_dir)

    def test_builder_initialization(self, builder: DigestEmailBuilder) -> None:
        """Test builder initializes correctly."""
        assert builder.templates_dir is not None
        assert builder.templates_dir.exists()
        assert (builder.templates_dir / "digest-email.html").exists()

    def test_build_digest(self, builder: DigestEmailBuilder) -> None:
        """Test building a digest email."""
        jobs = [
            DigestJob(
                id="job-1",
                title="Software Engineer",
                company="Tech Corp",
                location="Remote",
                match_score=85,
                score_summary="Great match",
                category="tech-devops",
                url="https://example.com/1",
                resume_url="https://r2.dev/1.pdf",
                cover_letter_url=None,
                cover_letter_requested=False,
            ),
            DigestJob(
                id="job-2",
                title="Server",
                company="Restaurant",
                location="Atlanta",
                match_score=75,
                score_summary="Good position",
                category="serving",
                url="https://example.com/2",
                resume_url="https://r2.dev/2.pdf",
                cover_letter_url=None,
                cover_letter_requested=False,
            ),
        ]

        stats = DigestStats(
            total_discovered=10,
            total_extracted=8,
            total_rejected=2,
            total_qualified=6,
            tech_count=4,
            serving_count=2,
        )

        html = builder.build_digest(jobs, stats, "2 jobs rejected for requiring 5+ years")

        assert "Software Engineer" in html
        assert "Tech Corp" in html
        assert "Server" in html
        assert "Restaurant" in html

    def test_build_digest_empty_jobs(self, builder: DigestEmailBuilder) -> None:
        """Test building a digest with no qualified jobs."""
        jobs = []

        stats = DigestStats(
            total_discovered=5,
            total_extracted=3,
            total_rejected=2,
            total_qualified=0,
            tech_count=0,
            serving_count=0,
        )

        html = builder.build_digest(jobs, stats, "All jobs rejected")

        assert "Software Engineer" not in html  # No jobs listed

    def test_build_plain_text(self, builder: DigestEmailBuilder) -> None:
        """Test converting HTML to plain text."""
        html = """
        <html>
        <body>
            <h1>Hello</h1>
            <p>This is a <strong>test</strong> paragraph.</p>
        </body>
        </html>
        """

        text = builder.build_plain_text(html)

        assert "Hello" in text
        assert "test" in text
        assert "<h1>" not in text
        assert "<strong>" not in text


class TestZephyrClient:
    """Tests for the ZephyrClient class."""

    @pytest.fixture
    def zephyr_client(self) -> ZephyrClient:
        """Create a ZephyrClient instance."""
        return ZephyrClient(
            base_url="https://test.workers.dev",
            api_key="test-api-key",
        )

    @pytest.mark.asyncio
    async def test_send_email_success(self, zephyr_client: ZephyrClient) -> None:
        """Test sending an email successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        zephyr_client._client = mock_client

        result = await zephyr_client.send_email(
            to="test@example.com",
            subject="Test Subject",
            html="<p>Test HTML</p>",
            text="Test plain text",
        )

        assert result["success"] is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_http_error(self, zephyr_client: ZephyrClient) -> None:
        """Test handling HTTP errors when sending email."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPError("Connection failed")
        )
        zephyr_client._client = mock_client

        result = await zephyr_client.send_email(
            to="test@example.com",
            subject="Test",
            html="<p>Test</p>",
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_zephyr_client_context_manager(self) -> None:
        """Test ZephyrClient as async context manager."""
        with patch.object(
            ZephyrClient, "_get_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            async with ZephyrClient(
                base_url="https://test.workers.dev",
                api_key="test-key",
            ) as client:
                assert client.base_url == "https://test.workers.dev"

    def test_base_url_trailing_slash(self) -> None:
        """Test that trailing slashes are removed from base URL."""
        client = ZephyrClient(
            base_url="https://test.workers.dev/",
            api_key="test-key",
        )

        assert client.base_url == "https://test.workers.dev"


class TestCreateDigestJobsFromDbJobs:
    """Tests for the conversion function."""

    def test_create_digest_jobs(self) -> None:
        """Test converting DB jobs to DigestJobs."""
        # Create mock DB jobs
        class MockDbJob:
            id = "job-123"
            title = "Software Engineer"
            company = "Acme Corp"
            location = "Remote"
            match_score = 85
            score_summary = "Great match"
            category = "tech-devops"
            url = "https://example.com/job"
            resume_r2_url = "https://r2.dev/resume.pdf"
            cover_letter_r2_url = "https://r2.dev/cover.pdf"
            cover_letter_requested = True

        db_jobs = [MockDbJob()]

        digest_jobs = create_digest_jobs_from_db_jobs(db_jobs)

        assert len(digest_jobs) == 1
        assert digest_jobs[0].id == "job-123"
        assert digest_jobs[0].title == "Software Engineer"
        assert digest_jobs[0].category == "tech-devops"

    def test_create_digest_jobs_missing_fields(self) -> None:
        """Test conversion with missing optional fields."""
        class MockDbJob:
            id = "job-456"
            title = None  # Missing title
            company = None
            location = None
            match_score = None
            score_summary = None
            category = None
            url = "https://example.com/job"
            resume_r2_url = None
            cover_letter_r2_url = None
            cover_letter_requested = False

        db_jobs = [MockDbJob()]

        digest_jobs = create_digest_jobs_from_db_jobs(db_jobs)

        assert digest_jobs[0].title == "Unknown"  # Default
        assert digest_jobs[0].match_score == 0  # Default
        assert digest_jobs[0].category == "tech-devops"  # Default


class TestSendDigest:
    """Tests for the send_digest function."""

    @pytest.mark.asyncio
    async def test_send_digest_success(self) -> None:
        """Test sending digest successfully."""
        jobs = [
            DigestJob(
                id="job-1",
                title="Engineer",
                company="Corp",
                location="Remote",
                match_score=80,
                score_summary="Good match",
                category="tech-devops",
                url="https://example.com",
                resume_url=None,
                cover_letter_url=None,
                cover_letter_requested=False,
            )
        ]

        stats = DigestStats(
            total_discovered=5,
            total_extracted=3,
            total_rejected=2,
            total_qualified=1,
            tech_count=1,
            serving_count=0,
        )

        with patch.object(
            DigestEmailBuilder, "__init__", return_value=None
        ) as mock_init, patch.object(
            DigestEmailBuilder, "build_digest", return_value="<html>digest</html>"
        ), patch.object(
            DigestEmailBuilder, "build_plain_text", return_value="digest"
        ), patch.object(
            ZephyrClient, "send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"success": True}

            result = await send_digest(
                jobs=jobs,
                stats=stats,
                rejected_summary="2 rejected",
                zephyr_url="https://test.workers.dev",
                zephyr_api_key="test-key",
                to_email="test@example.com",
            )

            assert result is True
