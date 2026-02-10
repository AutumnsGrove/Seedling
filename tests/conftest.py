"""Shared test fixtures for Seedling test suite."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from seedling.db import Database, Job
from seedling.notify.digest import DigestJob, DigestStats


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """In-memory-style SQLite database via tmp_path, schema initialized."""
    database = Database(db_path=tmp_path / "test.db")
    database.init_schema()
    return database


@pytest.fixture
def make_job():
    """Factory returning Job instances with sensible defaults + overrides."""
    _counter = 0

    def _make(**overrides) -> Job:
        nonlocal _counter
        _counter += 1
        defaults = {
            "id": f"job-{_counter}",
            "platform": "indeed",
            "url": f"https://indeed.com/jobs/{_counter}",
            "url_hash": f"hash{_counter}",
            "title": "Software Engineer",
            "company": "Acme Corp",
            "location": "Remote",
            "status": "discovered",
        }
        defaults.update(overrides)
        return Job(**defaults)

    return _make


@pytest.fixture
def make_digest_job():
    """Factory for DigestJob instances."""
    _counter = 0

    def _make(**overrides) -> DigestJob:
        nonlocal _counter
        _counter += 1
        defaults = {
            "id": f"digest-{_counter}",
            "title": "Software Engineer",
            "company": "Acme Corp",
            "location": "Remote",
            "match_score": 80,
            "score_summary": "Good match for your skills",
            "category": "tech-devops",
            "url": f"https://example.com/job/{_counter}",
            "resume_url": None,
            "cover_letter_url": None,
            "cover_letter_requested": False,
        }
        defaults.update(overrides)
        return DigestJob(**defaults)

    return _make


@pytest.fixture
def templates_dir() -> Path:
    """Points to real templates/ directory."""
    return Path(__file__).parent.parent / "templates"


@pytest.fixture
def mock_openai_response():
    """Factory building mock ChatCompletion from a content string."""

    def _make(content: str) -> MagicMock:
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        return response

    return _make


@pytest.fixture
def secrets_dict() -> dict:
    """Complete fake secrets dict."""
    return {
        "OPENROUTER_API_KEY": "test-key-123",
        "EXA_API_KEY": "exa-key-456",
        "TAVILY_API_KEY": "tavily-key-789",
        "R2_ACCOUNT_ID": "test-account",
        "R2_ACCESS_KEY_ID": "r2-access-key",
        "R2_SECRET_ACCESS_KEY": "r2-secret-key",
        "R2_BUCKET": "seedling-resumes",
        "R2_PUBLIC_URL": "https://pub-test.r2.dev",
        "ZEPHYR_URL": "https://test.workers.dev/send",
        "ZEPHYR_API_KEY": "zephyr-key",
        "SEEDLING_EMAIL": "test@example.com",
    }
