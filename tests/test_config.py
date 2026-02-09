"""Tests for the config module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from seedling.config import Config, Secrets, load_secrets


class TestConfig:
    """Tests for the Config class."""

    @pytest.fixture
    def temp_secrets_file(self) -> Path:
        """Create a temporary secrets file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            secrets = {
                "OPENROUTER_API_KEY": "test-key-123",
                "JSEARCH_API_KEY": "jsearch-key-999",
                "EXA_API_KEY": "exa-key-456",
                "TAVILY_API_KEY": "tavily-key-789",
                "R2_ACCOUNT_ID": "test-account",
                "R2_ACCESS_KEY_ID": "r2-access-key",
                "R2_SECRET_ACCESS_KEY": "r2-secret-key",
                "R2_BUCKET": "seedling-resumes",
                "ZEPHYR_URL": "https://test.workers.dev/send",
                "ZEPHYR_API_KEY": "zephyr-key",
                "SEEDLING_EMAIL": "test@example.com",
            }
            json.dump(secrets, f)
            return Path(f.name)

    @pytest.fixture
    def config(self, temp_secrets_file: Path) -> Config:
        """Create a Config instance with temp file."""
        return Config(secrets_path=temp_secrets_file)

    def test_load_secrets_success(self, config: Config) -> None:
        """Test loading secrets successfully."""
        secrets = config.load_secrets()

        assert "OPENROUTER_API_KEY" in secrets
        assert secrets["OPENROUTER_API_KEY"] == "test-key-123"
        assert secrets["R2_ACCOUNT_ID"] == "test-account"
        assert secrets["SEEDLING_EMAIL"] == "test@example.com"

    def test_load_secrets_caching(self, config: Config) -> None:
        """Test that secrets are cached after first load."""
        secrets1 = config.load_secrets()
        secrets2 = config.load_secrets()

        assert secrets1 is secrets2  # Same object reference

    def test_load_secrets_missing_file(self) -> None:
        """Test FileNotFoundError when secrets file is missing."""
        config = Config(secrets_path=Path("/nonexistent/secrets.json"))

        with pytest.raises(FileNotFoundError):
            config.load_secrets()

    def test_load_secrets_missing_required_key(self) -> None:
        """Test KeyError when required key is missing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            # Missing OPENROUTER_API_KEY
            secrets = {
                "R2_ACCOUNT_ID": "test-account",
                "R2_ACCESS_KEY_ID": "r2-access-key",
                "R2_SECRET_ACCESS_KEY": "r2-secret-key",
                "R2_BUCKET": "seedling-resumes",
                "ZEPHYR_URL": "https://test.workers.dev/send",
                "ZEPHYR_API_KEY": "zephyr-key",
                "SEEDLING_EMAIL": "test@example.com",
            }
            json.dump(secrets, f)
            f.flush()

            config = Config(secrets_path=Path(f.name))

            with pytest.raises(KeyError, match="Missing required secrets"):
                config.load_secrets()

    def test_load_secrets_optional_keys(self) -> None:
        """Test that optional keys default to empty string."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            secrets = {
                "OPENROUTER_API_KEY": "test-key-123",
                "JSEARCH_API_KEY": "jsearch-key",
                "R2_ACCOUNT_ID": "test-account",
                "R2_ACCESS_KEY_ID": "r2-access-key",
                "R2_SECRET_ACCESS_KEY": "r2-secret-key",
                "R2_BUCKET": "seedling-resumes",
                "ZEPHYR_URL": "https://test.workers.dev/send",
                "ZEPHYR_API_KEY": "zephyr-key",
                "SEEDLING_EMAIL": "test@example.com",
                # EXA_API_KEY and TAVILY_API_KEY omitted
            }
            json.dump(secrets, f)
            f.flush()

            config = Config(secrets_path=Path(f.name))
            loaded = config.load_secrets()

            assert loaded["EXA_API_KEY"] == ""
            assert loaded["TAVILY_API_KEY"] == ""

    def test_get_method(self, config: Config) -> None:
        """Test the get method for accessing secrets."""
        config.load_secrets()

        assert config.get("OPENROUTER_API_KEY") == "test-key-123"
        assert config.get("NONEXISTENT_KEY") is None
        assert config.get("NONEXISTENT_KEY", "default") == "default"

    def test_load_secrets_function(self, temp_secrets_file: Path) -> None:
        """Test the convenience load_secrets function."""
        secrets = load_secrets(temp_secrets_file)

        assert secrets["OPENROUTER_API_KEY"] == "test-key-123"


class TestSecretsTypedDict:
    """Tests for the Secrets TypedDict structure."""

    def test_secrets_type_annotations(self) -> None:
        """Test that Secrets has correct type annotations."""
        secrets: Secrets = {
            "OPENROUTER_API_KEY": "key1",
            "JSEARCH_API_KEY": "jsearch-key",
            "EXA_API_KEY": "key2",
            "TAVILY_API_KEY": "key3",
            "R2_ACCOUNT_ID": "account",
            "R2_ACCESS_KEY_ID": "access",
            "R2_SECRET_ACCESS_KEY": "secret",
            "R2_BUCKET": "bucket",
            "R2_WORKER_URL": "https://test.com",
            "ZEPHYR_URL": "https://test.com",
            "ZEPHYR_API_KEY": "zephyr",
            "SEEDLING_EMAIL": "test@example.com",
        }

        assert secrets["OPENROUTER_API_KEY"] == "key1"
        assert len(secrets) == 12
