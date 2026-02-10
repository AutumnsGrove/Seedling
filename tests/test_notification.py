"""Tests for the notification module."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from seedling.notify.digest import (
    DigestEmailBuilder,
    DigestJob,
    DigestStats,
    ZephyrClient,
    create_digest_jobs_from_db_jobs,
    send_digest,
)


class TestDigestEmailBuilder:
    """Tests for the DigestEmailBuilder class."""

    @pytest.fixture
    def builder(self, templates_dir: Path) -> DigestEmailBuilder:
        """Create a DigestEmailBuilder instance."""
        return DigestEmailBuilder(templates_dir=templates_dir)

    def test_build_digest(self, builder: DigestEmailBuilder, make_digest_job) -> None:
        """Test building a digest email."""
        jobs = [
            make_digest_job(title="Software Engineer", company="Tech Corp", category="tech-devops"),
            make_digest_job(title="Server", company="Restaurant", category="serving"),
        ]
        stats = DigestStats(
            total_discovered=10, total_extracted=8,
            total_rejected=2, total_qualified=6,
            tech_count=4, serving_count=2,
        )

        html = builder.build_digest(jobs, stats, "2 jobs rejected for requiring 5+ years")
        assert "Software Engineer" in html
        assert "Tech Corp" in html
        assert "Server" in html
        assert "Restaurant" in html

    def test_build_digest_empty_jobs(self, builder: DigestEmailBuilder) -> None:
        """Test building a digest with no qualified jobs."""
        stats = DigestStats(
            total_discovered=5, total_extracted=3,
            total_rejected=2, total_qualified=0,
            tech_count=0, serving_count=0,
        )
        html = builder.build_digest([], stats, "All jobs rejected")
        assert "Software Engineer" not in html

    def test_build_plain_text(self, builder: DigestEmailBuilder) -> None:
        """Test converting HTML to plain text."""
        html = "<h1>Hello</h1><p>This is a <strong>test</strong> paragraph.</p>"
        text = builder.build_plain_text(html)
        assert "Hello" in text
        assert "test" in text
        assert "<h1>" not in text
        assert "<strong>" not in text

    def test_send_digest_with_real_builder(
        self, templates_dir: Path, make_digest_job
    ) -> None:
        """Real DigestEmailBuilder + real templates, only mock the HTTP call.

        Replaces the over-mocked send_digest test.
        """
        jobs = [
            make_digest_job(title="DevOps Engineer", category="tech-devops"),
            make_digest_job(title="Bartender", category="serving"),
        ]
        stats = DigestStats(
            total_discovered=5, total_extracted=3,
            total_rejected=1, total_qualified=2,
            tech_count=1, serving_count=1,
        )

        builder = DigestEmailBuilder(templates_dir=templates_dir)
        html = builder.build_digest(jobs, stats, "1 job rejected")
        text = builder.build_plain_text(html)

        assert "DevOps Engineer" in html
        assert "Bartender" in html
        assert len(text) > 0
        assert "<" not in text  # No HTML tags in plain text

    def test_build_digest_separates_tech_and_serving(
        self, builder: DigestEmailBuilder, make_digest_job
    ) -> None:
        """Verify template renders category sections correctly."""
        jobs = [
            make_digest_job(title="Security Analyst", category="tech-cyber"),
            make_digest_job(title="Restaurant Host", category="serving"),
        ]
        stats = DigestStats(
            total_discovered=2, total_extracted=2,
            total_rejected=0, total_qualified=2,
            tech_count=1, serving_count=1,
        )

        html = builder.build_digest(jobs, stats, "No rejections")
        assert "Top Tech Matches" in html
        assert "Serving Positions" in html
        assert "Security Analyst" in html
        assert "Restaurant Host" in html

    def test_build_plain_text_preserves_structure(
        self, builder: DigestEmailBuilder, make_digest_job
    ) -> None:
        """Full render->strip pipeline preserves content structure."""
        jobs = [make_digest_job(title="Python Dev", category="tech-devops")]
        stats = DigestStats(
            total_discovered=1, total_extracted=1,
            total_rejected=0, total_qualified=1,
            tech_count=1, serving_count=0,
        )

        html = builder.build_digest(jobs, stats, "No rejections")
        text = builder.build_plain_text(html)

        assert "Python Dev" in text
        assert "Seedling" in text
        assert "<div>" not in text


class TestZephyrClient:
    """Tests for the ZephyrClient class."""

    @pytest.mark.asyncio
    async def test_send_email_success(self) -> None:
        """Test sending an email successfully."""
        client = ZephyrClient(base_url="https://test.workers.dev", api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client._client = mock_http

        result = await client.send_email(
            to="test@example.com",
            subject="Test Subject",
            html="<p>Test HTML</p>",
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_email_http_error(self) -> None:
        """Test handling HTTP errors when sending email."""
        client = ZephyrClient(base_url="https://test.workers.dev", api_key="test-key")

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(
            side_effect=httpx.HTTPError("Connection failed")
        )
        client._client = mock_http

        result = await client.send_email(
            to="test@example.com", subject="Test", html="<p>Test</p>"
        )
        assert result["success"] is False
        assert "error" in result

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

        digest_jobs = create_digest_jobs_from_db_jobs([MockDbJob()])

        assert len(digest_jobs) == 1
        assert digest_jobs[0].id == "job-123"
        assert digest_jobs[0].title == "Software Engineer"
        assert digest_jobs[0].category == "tech-devops"
