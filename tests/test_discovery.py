"""Tests for the discovery module."""

from unittest.mock import patch

import pytest

from seedling.discovery import DiscoveredJob, generate_url_hash
from seedling.discovery.jobspy import JobSpyDiscovery, SearchConfig


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
            "company": [np.nan],
            "location": [np.nan],
            "description": ["A real description here"],
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
        assert jobs[0].company is None
        assert jobs[0].location is None
        assert jobs[0].salary_min is None
        assert jobs[0].salary_max is None
        assert jobs[0].published_at is None
