"""Tests for the database module."""

import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from seedling.db import Database, Job, Run, get_database


class TestJob:
    """Tests for the Job dataclass."""

    def test_job_creation(self) -> None:
        """Test creating a Job instance."""
        job = Job(
            id="test-id-123",
            platform="indeed",
            url="https://www.indeed.com/viewjob?jk=abc123",
            url_hash="abc123hash",
            title="Software Engineer",
            company="Acme Corp",
            location="Remote",
        )

        assert job.id == "test-id-123"
        assert job.platform == "indeed"
        assert job.title == "Software Engineer"
        assert job.company == "Acme Corp"
        assert job.status == "discovered"  # Default value

    def test_job_with_optional_fields(self) -> None:
        """Test creating a Job with all optional fields."""
        now = datetime.now().isoformat()
        job = Job(
            id="test-id",
            platform="linkedin",
            url="https://linkedin.com/jobs/view/123",
            url_hash="hash123",
            title="Senior Developer",
            company="Tech Corp",
            location="Atlanta, GA",
            remote=True,
            salary_min=100000,
            salary_max=150000,
            salary_text="$100k-$150k",
            description="Full description",
            requirements="Requirements text",
            preferred="Nice to have",
            category="tech-devops",
            match_score=85,
            score_breakdown='{"skill": 90, "growth": 80}',
            score_summary="Great match for your skills",
            quick_reject_reason=None,
            status="qualified",
            resume_r2_url="https://r2.dev/resume.pdf",
            cover_letter_r2_url="https://r2.dev/cover.pdf",
            cover_letter_requested=True,
            shutter_pi_detected=False,
            discovered_at=now,
            extracted_at=now,
            scored_at=now,
        )

        assert job.remote is True
        assert job.salary_min == 100000
        assert job.match_score == 85
        assert job.category == "tech-devops"
        assert job.cover_letter_requested is True

    def test_job_to_dict(self) -> None:
        """Test converting Job to dictionary."""
        job = Job(
            id="test-id",
            platform="indeed",
            url="https://indeed.com/jobs/view/123",
            url_hash="hash123",
            title="Engineer",
            company="Corp",
            status="discovered",
        )

        result = job.to_dict()

        assert result["id"] == "test-id"
        assert result["platform"] == "indeed"
        assert result["title"] == "Engineer"
        assert isinstance(result, dict)


class TestRun:
    """Tests for the Run dataclass."""

    def test_run_creation(self) -> None:
        """Test creating a Run instance."""
        run = Run(
            id="run-123",
            started_at="2024-01-01T10:00:00",
        )

        assert run.id == "run-123"
        assert run.discovered == 0  # Default
        assert run.email_sent is False  # Default

    def test_run_with_stats(self) -> None:
        """Test creating a Run with statistics."""
        run = Run(
            id="run-456",
            started_at="2024-01-01T10:00:00",
            completed_at="2024-01-01T10:30:00",
            discovered=10,
            extracted=8,
            quick_rejected=2,
            scored=8,
            qualified=5,
            resumes_generated=3,
            email_sent=True,
            duration_seconds=1800.0,
        )

        assert run.discovered == 10
        assert run.extracted == 8
        assert run.quick_rejected == 2
        assert run.email_sent is True
        assert run.duration_seconds == 1800.0


class TestDatabase:
    """Tests for the Database class."""

    @pytest.fixture
    def temp_db_path(self) -> Path:
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def db(self, temp_db_path: Path) -> Database:
        """Create a Database instance with temp path."""
        database = Database(db_path=temp_db_path)
        database.init_schema()
        return database

    def test_init_schema(self, db: Database) -> None:
        """Test database schema initialization."""
        with db.connect() as conn:
            # Check that tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]

            assert "jobs" in table_names
            assert "runs" in table_names

    def test_upsert_job(self, db: Database) -> None:
        """Test inserting and updating a job."""
        job = Job(
            id="job-1",
            platform="indeed",
            url="https://indeed.com/jobs/view/1",
            url_hash="hash1",
            title="Software Engineer",
            company="Acme Corp",
        )

        db.upsert_job(job)

        # Verify it was inserted
        retrieved = db.get_job_by_url_hash("hash1")
        assert retrieved is not None
        assert retrieved.title == "Software Engineer"
        assert retrieved.company == "Acme Corp"

        # Update the job
        job.match_score = 85
        job.status = "qualified"
        db.upsert_job(job)

        # Verify update
        retrieved = db.get_job_by_url_hash("hash1")
        assert retrieved is not None
        assert retrieved.match_score == 85
        assert retrieved.status == "qualified"

    def test_get_job_by_url_hash_not_found(self, db: Database) -> None:
        """Test getting a non-existent job."""
        result = db.get_job_by_url_hash("nonexistent-hash")
        assert result is None

    def test_get_jobs_by_status(self, db: Database) -> None:
        """Test getting jobs by status."""
        # Insert jobs with different statuses
        job1 = Job(
            id="job-1",
            platform="indeed",
            url="https://indeed.com/jobs/1",
            url_hash="hash1",
            status="qualified",
        )
        job2 = Job(
            id="job-2",
            platform="linkedin",
            url="https://linkedin.com/jobs/2",
            url_hash="hash2",
            status="qualified",
        )
        job3 = Job(
            id="job-3",
            platform="indeed",
            url="https://indeed.com/jobs/3",
            url_hash="hash3",
            status="rejected",
        )

        db.upsert_job(job1)
        db.upsert_job(job2)
        db.upsert_job(job3)

        qualified = db.get_jobs_by_status("qualified")
        assert len(qualified) == 2

        rejected = db.get_jobs_by_status("rejected")
        assert len(rejected) == 1

    def test_get_jobs_by_status_with_limit(self, db: Database) -> None:
        """Test getting jobs with limit."""
        for i in range(5):
            job = Job(
                id=f"job-{i}",
                platform="indeed",
                url=f"https://indeed.com/jobs/{i}",
                url_hash=f"hash{i}",
                status="qualified",
            )
            db.upsert_job(job)

        results = db.get_jobs_by_status("qualified", limit=3)
        assert len(results) == 3

    def test_create_and_update_run(self, db: Database) -> None:
        """Test creating and updating a run."""
        run = Run(
            id="run-1",
            started_at="2024-01-01T10:00:00",
            discovered=5,
        )

        db.create_run(run)

        # Update the run
        run.completed_at = "2024-01-01T10:30:00"
        run.extracted = 4
        run.quick_rejected = 1
        run.scored = 4
        run.qualified = 2
        run.email_sent = True
        run.duration_seconds = 1800.0

        db.update_run(run)

        # Note: We don't have a get_run method, but we can verify
        # the update didn't raise an error

    def test_get_database_function(self, temp_db_path: Path) -> None:
        """Test the get_database convenience function."""
        db = get_database(temp_db_path)

        assert db.db_path == temp_db_path
        # Schema should be initialized
        with db.connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            assert len(tables) >= 2

    def test_job_url_hash_uniqueness(self, db: Database) -> None:
        """Test that URL hash uniqueness is enforced."""
        job1 = Job(
            id="job-1",
            platform="indeed",
            url="https://indeed.com/jobs/1",
            url_hash="same-hash",
            title="First Job",
        )
        job2 = Job(
            id="job-2",
            platform="linkedin",
            url="https://linkedin.com/jobs/1",
            url_hash="same-hash",  # Same hash
            title="Second Job",
        )

        db.upsert_job(job1)
        db.upsert_job(job2)  # Should replace due to OR REPLACE

        retrieved = db.get_job_by_url_hash("same-hash")
        assert retrieved is not None
        assert retrieved.title == "Second Job"  # Should be the latest
