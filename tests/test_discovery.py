"""Tests for the discovery module."""

from unittest.mock import patch

import pytest

from seedling.discovery import DiscoveredJob, generate_url_hash
from seedling.discovery.jobspy import JobSpyDiscovery, SearchConfig, _is_junk_listing


class TestGenerateUrlHash:
    """Tests for URL hash generation."""

    def test_generate_url_hash_consistency(self) -> None:
        """Same URL should produce same hash."""
        url = "https://www.indeed.com/viewjob?jk=abc123"
        assert generate_url_hash(url) == generate_url_hash(url)

    def test_generate_url_hash_different_urls(self) -> None:
        """Different URLs should produce different hashes."""
        hash1 = generate_url_hash("https://www.indeed.com/viewjob?jk=abc123")
        hash2 = generate_url_hash("https://www.indeed.com/viewjob?jk=def456")
        assert hash1 != hash2

    def test_generate_url_hash_format(self) -> None:
        """Hash should be valid SHA-256 hex string."""
        hash_str = generate_url_hash("https://www.indeed.com/viewjob?jk=abc123")
        assert len(hash_str) == 64
        assert all(c in "0123456789abcdef" for c in hash_str)


class TestJobSpyDiscovery:
    """Tests for JobSpy discovery."""

    def test_deduplication(self) -> None:
        """Test that discover_all_sync deduplicates by URL hash."""
        import pandas as pd

        mock_df = pd.DataFrame({
            "job_url": [
                "https://example.com/job1",
                "https://example.com/job1",
                "https://example.com/job2",
            ],
            "title": ["Job 1", "Job 1 Duplicate", "Job 2"],
            "company": ["Co1", "Co1", "Co2"],
            "location": ["Remote", "Remote", "Atlanta"],
            "description": ["Desc 1" * 50, "Desc 1" * 50, "Desc 2" * 50],
            "is_remote": [True, True, False],
            "min_amount": [None, None, 50000],
            "max_amount": [None, None, 80000],
            "date_posted": [None, None, "2024-01-01"],
            "site": ["indeed", "indeed", "google"],
        })

        discovery = JobSpyDiscovery(
            tech_searches=[SearchConfig(query="test", location="", category="tech")],
            serving_searches=[],
        )

        with patch("seedling.discovery.jobspy.scrape_jobs", return_value=mock_df):
            jobs = discovery.discover_all_sync()

        assert len(jobs) == 2
        urls = [j.url for j in jobs]
        assert "https://example.com/job1" in urls
        assert "https://example.com/job2" in urls

    def test_run_search_handles_empty_result(self) -> None:
        """Test that _run_search handles empty DataFrame."""
        import pandas as pd

        discovery = JobSpyDiscovery()
        config = SearchConfig(query="test", location="", category="tech")

        with patch("seedling.discovery.jobspy.scrape_jobs", return_value=pd.DataFrame()):
            jobs = discovery._run_search(config)

        assert jobs == []

    def test_run_search_handles_exception(self) -> None:
        """Test that _run_search handles exceptions gracefully."""
        discovery = JobSpyDiscovery()
        config = SearchConfig(query="test", location="", category="tech")

        with patch(
            "seedling.discovery.jobspy.scrape_jobs",
            side_effect=Exception("API error"),
        ):
            jobs = discovery._run_search(config)

        assert jobs == []

    def test_run_search_parses_salary(self) -> None:
        """Test that _run_search correctly parses salary fields."""
        import pandas as pd

        mock_df = pd.DataFrame({
            "job_url": ["https://example.com/job1"],
            "title": ["Engineer"],
            "company": ["Corp"],
            "location": ["Remote"],
            "description": ["A" * 300],
            "is_remote": [True],
            "min_amount": [80000.0],
            "max_amount": [120000.0],
            "date_posted": ["2024-06-15"],
            "site": ["indeed"],
        })

        discovery = JobSpyDiscovery()
        config = SearchConfig(query="test", location="", category="tech")

        with patch("seedling.discovery.jobspy.scrape_jobs", return_value=mock_df):
            jobs = discovery._run_search(config)

        assert len(jobs) == 1
        assert jobs[0].salary_min == 80000
        assert jobs[0].salary_max == 120000
        assert jobs[0].is_remote is True

    def test_run_search_handles_nan_fields(self) -> None:
        """Real pandas NaN (not string 'nan') produces None for optional fields."""
        import pandas as pd
        import numpy as np

        mock_df = pd.DataFrame({
            "job_url": ["https://example.com/nan-job"],
            "title": ["Engineer"],
            "company": ["Acme Corp"],
            "location": [np.nan],
            "description": ["A real description that is long enough to pass the junk filter threshold easily"],
            "is_remote": [False],
            "min_amount": [np.nan],
            "max_amount": [np.nan],
            "date_posted": [np.nan],
            "site": ["indeed"],
        })

        discovery = JobSpyDiscovery()
        config = SearchConfig(query="test", location="", category="tech")

        with patch("seedling.discovery.jobspy.scrape_jobs", return_value=mock_df):
            jobs = discovery._run_search(config)

        assert len(jobs) == 1
        assert jobs[0].company == "Acme Corp"
        assert jobs[0].location is None
        assert jobs[0].salary_min is None
        assert jobs[0].salary_max is None
        assert jobs[0].published_at is None


class TestJunkListingFilter:
    """Tests for _is_junk_listing filter."""

    def test_aggregator_page_title(self) -> None:
        """Titles like '2,000+ Cyber Security jobs' are junk."""
        assert _is_junk_listing(
            "2,000+ Cyber Security Entry Level jobs in United States (125 new)",
            "Some Company",
            "Remote",
            "A" * 100,
        )

    def test_numeric_jobs_title_variants(self) -> None:
        """Various aggregator title patterns."""
        assert _is_junk_listing("150 Python Developer jobs", "Co", "NYC", "A" * 100)
        assert _is_junk_listing("1,234 Security Analyst Jobs in Atlanta", "Co", "ATL", "A" * 100)
        assert _is_junk_listing("50+ DevOps jobs near me", "Co", "Remote", "A" * 100)

    def test_no_company_and_no_location(self) -> None:
        """Missing both company and location is junk."""
        assert _is_junk_listing("Software Engineer", None, None, "A" * 100)
        assert _is_junk_listing("Software Engineer", "", "", "A" * 100)

    def test_short_description(self) -> None:
        """Very short descriptions are junk."""
        assert _is_junk_listing("Software Engineer", "Acme", "Remote", "Apply now")

    def test_real_listing_passes(self) -> None:
        """A real job listing should not be filtered."""
        assert not _is_junk_listing(
            "Junior Software Engineer",
            "Acme Corp",
            "Atlanta, GA",
            "We are looking for a junior software engineer to join our team. "
            "Requirements: Python, JavaScript, SQL. Remote-friendly position.",
        )

    def test_company_only_passes(self) -> None:
        """Having company but no location is fine."""
        assert not _is_junk_listing(
            "DevOps Engineer",
            "TechCo",
            None,
            "A" * 100,
        )

    def test_location_only_passes(self) -> None:
        """Having location but no company is fine."""
        assert not _is_junk_listing(
            "Server",
            None,
            "Atlanta, GA",
            "A" * 100,
        )

    def test_run_search_filters_junk(self) -> None:
        """Integration: _run_search drops junk listings from results."""
        import pandas as pd

        mock_df = pd.DataFrame({
            "job_url": [
                "https://example.com/job1",
                "https://example.com/aggregator",
                "https://example.com/job3",
            ],
            "title": [
                "Junior DevOps Engineer",
                "2,000+ Cyber Security Entry Level jobs in United States",
                "Python Developer",
            ],
            "company": ["Acme", None, "TechCo"],
            "location": ["Remote", None, "Atlanta"],
            "description": ["A" * 100, "Short", "B" * 100],
            "is_remote": [True, False, False],
            "min_amount": [None, None, None],
            "max_amount": [None, None, None],
            "date_posted": [None, None, None],
            "site": ["indeed", "indeed", "google"],
        })

        discovery = JobSpyDiscovery(
            tech_searches=[SearchConfig(query="test", location="", category="tech")],
            serving_searches=[],
        )

        with patch("seedling.discovery.jobspy.scrape_jobs", return_value=mock_df):
            jobs = discovery._run_search(
                SearchConfig(query="test", location="", category="tech")
            )

        assert len(jobs) == 2
        titles = [j.title for j in jobs]
        assert "Junior DevOps Engineer" in titles
        assert "Python Developer" in titles
