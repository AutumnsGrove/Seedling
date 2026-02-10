"""Tests for the database module."""

from pathlib import Path

import pytest

from seedling.db import Database, Job, Run, get_database


class TestDatabase:
    """Tests for the Database class."""

    def test_init_schema(self, db: Database) -> None:
        """Test database schema initialization."""
        with db.connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]

            assert "jobs" in table_names
            assert "runs" in table_names

    def test_upsert_job(self, db: Database, make_job) -> None:
        """Test inserting and updating a job."""
        job = make_job(title="Software Engineer", company="Acme Corp")
        db.upsert_job(job)

        retrieved = db.get_job_by_url_hash(job.url_hash)
        assert retrieved is not None
        assert retrieved.title == "Software Engineer"
        assert retrieved.company == "Acme Corp"

        # Update the job
        job.match_score = 85
        job.status = "qualified"
        db.upsert_job(job)

        retrieved = db.get_job_by_url_hash(job.url_hash)
        assert retrieved is not None
        assert retrieved.match_score == 85
        assert retrieved.status == "qualified"

    def test_upsert_preserves_existing_fields_via_coalesce(
        self, db: Database, make_job
    ) -> None:
        """Upsert with NULL title doesn't erase existing title.

        Regression test for the COALESCE fix in the upsert query.
        """
        job = make_job(title="Original Title", url_hash="same-hash")
        db.upsert_job(job)

        # Second upsert with None title — should keep "Original Title"
        job2 = make_job(title=None, url_hash="same-hash", status="extracted")
        db.upsert_job(job2)

        retrieved = db.get_job_by_url_hash("same-hash")
        assert retrieved is not None
        assert retrieved.title == "Original Title"
        assert retrieved.status == "extracted"

    def test_get_job_by_url_hash_not_found(self, db: Database) -> None:
        """Test getting a non-existent job."""
        result = db.get_job_by_url_hash("nonexistent-hash")
        assert result is None

    def test_get_jobs_by_status(self, db: Database, make_job) -> None:
        """Test getting jobs by status."""
        db.upsert_job(make_job(url_hash="h1", status="qualified"))
        db.upsert_job(make_job(url_hash="h2", status="qualified"))
        db.upsert_job(make_job(url_hash="h3", status="rejected"))

        assert len(db.get_jobs_by_status("qualified")) == 2
        assert len(db.get_jobs_by_status("rejected")) == 1

    def test_get_jobs_by_status_with_limit(self, db: Database, make_job) -> None:
        """Test getting jobs with limit."""
        for i in range(5):
            db.upsert_job(make_job(url_hash=f"lim-{i}", status="qualified"))

        results = db.get_jobs_by_status("qualified", limit=3)
        assert len(results) == 3

    def test_get_qualified_jobs_time_filter(self, db: Database, make_job) -> None:
        """Time-based filtering works in get_qualified_jobs."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        job = make_job(
            url_hash="recent", status="qualified",
            match_score=90, discovered_at=now,
        )
        db.upsert_job(job)

        results = db.get_qualified_jobs(days=1)
        assert len(results) == 1
        assert results[0].match_score == 90

    def test_get_stats_counts_statuses(self, db: Database, make_job) -> None:
        """Verify get_stats counts by status."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        db.upsert_job(make_job(url_hash="s1", status="extracted", discovered_at=now))
        db.upsert_job(make_job(url_hash="s2", status="rejected", discovered_at=now))
        db.upsert_job(make_job(url_hash="s3", status="rejected", discovered_at=now))
        db.upsert_job(make_job(url_hash="s4", status="qualified", discovered_at=now))

        stats = db.get_stats()
        assert stats["total"] == 4
        assert stats["extracted"] == 1
        assert stats["rejected"] == 2
        assert stats["qualified"] == 1

    def test_create_and_update_run(self, db: Database) -> None:
        """Test creating and updating a run."""
        run = Run(id="run-1", started_at="2024-01-01T10:00:00", discovered=5)
        db.create_run(run)

        run.completed_at = "2024-01-01T10:30:00"
        run.extracted = 4
        run.qualified = 2
        run.email_sent = True
        run.duration_seconds = 1800.0
        db.update_run(run)

    def test_get_database_function(self, tmp_path: Path) -> None:
        """Test the get_database convenience function."""
        db = get_database(tmp_path / "conv.db")
        with db.connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            assert len(tables) >= 2

    def test_job_url_hash_uniqueness(self, db: Database, make_job) -> None:
        """Test that URL hash uniqueness is enforced via upsert."""
        db.upsert_job(make_job(url_hash="same-hash", title="First Job"))
        db.upsert_job(make_job(url_hash="same-hash", title="Second Job"))

        retrieved = db.get_job_by_url_hash("same-hash")
        assert retrieved is not None
        assert retrieved.title == "Second Job"
