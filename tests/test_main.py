"""Tests for main.py pure functions."""

import pytest

from seedling.db import Database, Job
from seedling.main import _infer_category, _calc_stats, _get_rejected_summary
from seedling.notify.digest import DigestStats


class TestInferCategory:
    """Tests for _infer_category."""

    def test_infer_category_serving_keywords(self, make_job) -> None:
        """'Restaurant Server' → 'serving'."""
        job = make_job(title="Restaurant Server", description="Serve food and drinks")
        assert _infer_category(job) == "serving"

    def test_infer_category_bare_server_not_serving(self, make_job) -> None:
        """'Server Engineer' with Linux desc → tech, NOT serving.

        Regression test for the real bug where 'server' triggered serving.
        """
        job = make_job(
            title="Server Engineer",
            description="Manage Linux infrastructure and platform deployments",
        )
        result = _infer_category(job)
        assert result != "serving"
        assert result.startswith("tech")

    def test_infer_category_tech_cyber(self, make_job) -> None:
        """'cybersecurity' → 'tech-cyber'."""
        job = make_job(title="Cybersecurity Analyst", description="Security operations")
        assert _infer_category(job) == "tech-cyber"

    def test_infer_category_tech_fullstack(self, make_job) -> None:
        """'full stack developer' → 'tech-fullstack'."""
        job = make_job(title="Full Stack Developer", description="React and Python")
        assert _infer_category(job) == "tech-fullstack"

    def test_infer_category_tech_devops(self, make_job) -> None:
        """'devops' → 'tech-devops'."""
        job = make_job(title="DevOps Engineer", description="CI/CD pipelines")
        assert _infer_category(job) == "tech-devops"

    def test_infer_category_default(self, make_job) -> None:
        """Generic 'Software Engineer' → default 'tech-devops'."""
        job = make_job(title="Software Engineer", description="Write code")
        assert _infer_category(job) == "tech-devops"


class TestCalcStats:
    """Tests for _calc_stats."""

    def test_calc_stats_counts_correctly(self, make_job) -> None:
        """Mixed statuses produce correct DigestStats fields."""
        jobs = [
            make_job(status="discovered"),
            make_job(status="extracted", extracted_at="2024-01-01"),
            make_job(status="rejected", extracted_at="2024-01-01"),
            make_job(status="qualified", extracted_at="2024-01-01", category="tech-devops"),
            make_job(status="emailed", extracted_at="2024-01-01", category="tech-cyber"),
            make_job(status="qualified", extracted_at="2024-01-01", category="serving"),
        ]

        stats = _calc_stats(jobs)

        assert isinstance(stats, DigestStats)
        assert stats.total_discovered == 6
        assert stats.total_extracted == 5  # All except first
        assert stats.total_rejected == 1
        assert stats.total_qualified == 3  # qualified + emailed
        assert stats.tech_count == 2
        assert stats.serving_count == 1

    def test_calc_stats_empty_list(self) -> None:
        """Empty list → all zeros."""
        stats = _calc_stats([])

        assert stats.total_discovered == 0
        assert stats.total_extracted == 0
        assert stats.total_rejected == 0
        assert stats.total_qualified == 0
        assert stats.tech_count == 0
        assert stats.serving_count == 0


class TestGetRejectedSummary:
    """Tests for _get_rejected_summary."""

    def test_get_rejected_summary_groups_reasons(self, db: Database, make_job) -> None:
        """Insert rejected jobs in real DB, verify grouped output."""
        db.upsert_job(make_job(
            url_hash="r1", status="rejected",
            quick_reject_reason="Requires 5+ years experience",
        ))
        db.upsert_job(make_job(
            url_hash="r2", status="rejected",
            quick_reject_reason="Requires 5+ years experience",
        ))
        db.upsert_job(make_job(
            url_hash="r3", status="rejected",
            quick_reject_reason="Senior level role",
        ))

        summary = _get_rejected_summary(db)

        assert "Rejection reasons:" in summary
        assert "Requires 5+ years experience: 2" in summary
        assert "Senior level role: 1" in summary
