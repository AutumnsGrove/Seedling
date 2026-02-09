"""Database module for Seedling.

Manages SQLite database for job tracking and history.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional


@dataclass
class Job:
    """Represents a job listing in the database."""

    id: str
    platform: str
    url: str
    url_hash: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_text: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    preferred: Optional[str] = None
    category: Optional[str] = None
    match_score: Optional[int] = None
    score_breakdown: Optional[str] = None
    score_summary: Optional[str] = None
    quick_reject_reason: Optional[str] = None
    status: str = "discovered"
    resume_r2_url: Optional[str] = None
    cover_letter_r2_url: Optional[str] = None
    cover_letter_requested: bool = False
    shutter_pi_detected: bool = False
    discovered_at: Optional[str] = None
    extracted_at: Optional[str] = None
    scored_at: Optional[str] = None
    emailed_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "platform": self.platform,
            "url": self.url,
            "url_hash": self.url_hash,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "remote": self.remote,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_text": self.salary_text,
            "description": self.description,
            "requirements": self.requirements,
            "preferred": self.preferred,
            "category": self.category,
            "match_score": self.match_score,
            "score_breakdown": self.score_breakdown,
            "score_summary": self.score_summary,
            "quick_reject_reason": self.quick_reject_reason,
            "status": self.status,
            "resume_r2_url": self.resume_r2_url,
            "cover_letter_r2_url": self.cover_letter_r2_url,
            "cover_letter_requested": self.cover_letter_requested,
            "shutter_pi_detected": self.shutter_pi_detected,
            "discovered_at": self.discovered_at,
            "extracted_at": self.extracted_at,
            "scored_at": self.scored_at,
            "emailed_at": self.emailed_at,
        }


@dataclass
class Run:
    """Represents a run of the Seedling pipeline."""

    id: str
    started_at: str
    completed_at: Optional[str] = None
    discovered: int = 0
    extracted: int = 0
    quick_rejected: int = 0
    scored: int = 0
    qualified: int = 0
    resumes_generated: int = 0
    email_sent: bool = False
    errors: Optional[str] = None
    duration_seconds: Optional[float] = None


class Database:
    """SQLite database manager for Seedling."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.seedling/seedling.db
        """
        if db_path is None:
            db_path = Path.home() / ".seedling" / "seedling.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initialize database schema."""
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    url TEXT NOT NULL,
                    url_hash TEXT UNIQUE NOT NULL,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    remote BOOLEAN DEFAULT FALSE,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    salary_text TEXT,
                    description TEXT,
                    requirements TEXT,
                    preferred TEXT,
                    category TEXT,
                    match_score INTEGER,
                    score_breakdown TEXT,
                    score_summary TEXT,
                    quick_reject_reason TEXT,
                    status TEXT DEFAULT 'discovered',
                    resume_r2_url TEXT,
                    cover_letter_r2_url TEXT,
                    cover_letter_requested BOOLEAN DEFAULT FALSE,
                    shutter_pi_detected BOOLEAN DEFAULT FALSE,
                    discovered_at TEXT DEFAULT (datetime('now')),
                    extracted_at TEXT,
                    scored_at TEXT,
                    emailed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    discovered INTEGER DEFAULT 0,
                    extracted INTEGER DEFAULT 0,
                    quick_rejected INTEGER DEFAULT 0,
                    scored INTEGER DEFAULT 0,
                    qualified INTEGER DEFAULT 0,
                    resumes_generated INTEGER DEFAULT 0,
                    email_sent BOOLEAN DEFAULT FALSE,
                    errors TEXT,
                    duration_seconds REAL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_date ON jobs(discovered_at DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category);
            """)

    def upsert_job(self, job: Job) -> None:
        """Insert or update a job.

        Args:
            job: Job to upsert.
        """
        with self.connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO jobs (
                    id, platform, url, url_hash, title, company, location, remote,
                    salary_min, salary_max, salary_text, description, requirements,
                    preferred, category, match_score, score_breakdown, score_summary,
                    quick_reject_reason, status, resume_r2_url, cover_letter_r2_url,
                    cover_letter_requested, shutter_pi_detected, discovered_at,
                    extracted_at, scored_at, emailed_at
                ) VALUES (
                    :id, :platform, :url, :url_hash, :title, :company, :location, :remote,
                    :salary_min, :salary_max, :salary_text, :description, :requirements,
                    :preferred, :category, :match_score, :score_breakdown, :score_summary,
                    :quick_reject_reason, :status, :resume_r2_url, :cover_letter_r2_url,
                    :cover_letter_requested, :shutter_pi_detected, :discovered_at,
                    :extracted_at, :scored_at, :emailed_at
                )
            """, job.to_dict())
            conn.commit()

    def get_job_by_url_hash(self, url_hash: str) -> Optional[Job]:
        """Get a job by its URL hash.

        Args:
            url_hash: SHA-256 hash of the URL.

        Returns:
            Job if found, None otherwise.
        """
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE url_hash = ?",
                (url_hash,)
            ).fetchone()

        if row is None:
            return None

        return self._row_to_job(row)

    def get_jobs_by_status(
        self, status: str, limit: int = 100
    ) -> list[Job]:
        """Get jobs by status.

        Args:
            status: Job status to filter by.
            limit: Maximum number of jobs to return.

        Returns:
            List of jobs.
        """
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY discovered_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_qualified_jobs(self, days: int = 1) -> list[Job]:
        """Get jobs that passed scoring and need tailoring.

        Args:
            days: Only get jobs from the last N days.

        Returns:
            List of qualified jobs.
        """
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs
                WHERE status = 'qualified'
                AND discovered_at >= datetime('now', ?)
                ORDER BY match_score DESC
            """, (f"-{days} days",)).fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_todays_jobs(self) -> list[Job]:
        """Get all jobs discovered today.

        Returns:
            List of today's jobs.
        """
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs
                WHERE discovered_at >= datetime('now', 'start of day')
                ORDER BY match_score DESC
            """).fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_stats(self) -> dict:
        """Get run statistics.

        Returns:
            Dict with stats about today's run.
        """
        with self.connect() as conn:
            today = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'extracted' THEN 1 ELSE 0 END) as extracted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN status = 'qualified' THEN 1 ELSE 0 END) as qualified,
                    SUM(CASE WHEN status = 'emailed' THEN 1 ELSE 0 END) as emailed
                FROM jobs
                WHERE discovered_at >= datetime('now', 'start of day')
            """).fetchone()

            return dict(today) if today else {}

    def create_run(self, run: Run) -> None:
        """Create a new run record.

        Args:
            run: Run to create.
        """
        with self.connect() as conn:
            conn.execute("""
                INSERT INTO runs (
                    id, started_at, discovered
                ) VALUES (?, ?, ?)
            """, (run.id, run.started_at, run.discovered))
            conn.commit()

    def update_run(self, run: Run) -> None:
        """Update a run record.

        Args:
            run: Run to update.
        """
        with self.connect() as conn:
            conn.execute("""
                UPDATE runs SET
                    completed_at = :completed_at,
                    discovered = :discovered,
                    extracted = :extracted,
                    quick_rejected = :quick_rejected,
                    scored = :scored,
                    qualified = :qualified,
                    resumes_generated = :resumes_generated,
                    email_sent = :email_sent,
                    errors = :errors,
                    duration_seconds = :duration_seconds
                WHERE id = :id
            """, {
                "id": run.id,
                "completed_at": run.completed_at,
                "discovered": run.discovered,
                "extracted": run.extracted,
                "quick_rejected": run.quick_rejected,
                "scored": run.scored,
                "qualified": run.qualified,
                "resumes_generated": run.resumes_generated,
                "email_sent": run.email_sent,
                "errors": run.errors,
                "duration_seconds": run.duration_seconds,
            })
            conn.commit()

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convert a database row to a Job object."""
        return Job(
            id=row["id"],
            platform=row["platform"],
            url=row["url"],
            url_hash=row["url_hash"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            remote=bool(row["remote"]),
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_text=row["salary_text"],
            description=row["description"],
            requirements=row["requirements"],
            preferred=row["preferred"],
            category=row["category"],
            match_score=row["match_score"],
            score_breakdown=row["score_breakdown"],
            score_summary=row["score_summary"],
            quick_reject_reason=row["quick_reject_reason"],
            status=row["status"],
            resume_r2_url=row["resume_r2_url"],
            cover_letter_r2_url=row["cover_letter_r2_url"],
            cover_letter_requested=bool(row["cover_letter_requested"]),
            shutter_pi_detected=bool(row["shutter_pi_detected"]),
            discovered_at=row["discovered_at"],
            extracted_at=row["extracted_at"],
            scored_at=row["scored_at"],
            emailed_at=row["emailed_at"],
        )


def get_database(db_path: Optional[Path] = None) -> Database:
    """Get a Database instance.

    Convenience function.

    Args:
        db_path: Optional path to database.

    Returns:
        Database instance.
    """
    db = Database(db_path)
    db.init_schema()
    return db
