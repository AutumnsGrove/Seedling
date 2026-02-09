"""Configuration loader for Seedling.

Loads secrets from secrets.json in project root or ~/.seedling/secrets.json

Priority:
1. ./secrets.json (project root - for local development)
2. ~/.seedling/secrets.json (home directory - for production)
"""

import json
import os
from pathlib import Path
from typing import Any, TypedDict


class Secrets(TypedDict):
    """All required secrets for Seedling."""

    OPENROUTER_API_KEY: str
    EXA_API_KEY: str
    TAVILY_API_KEY: str
    JSEARCH_API_KEY: str
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET: str
    R2_WORKER_URL: str
    ZEPHYR_URL: str
    ZEPHYR_API_KEY: str
    SEEDLING_EMAIL: str


def find_secrets_file() -> Path | None:
    """Find secrets.json file.

    Checks:
    1. ./secrets.json (project root)
    2. ~/.seedling/secrets.json (home directory)

    Returns:
        Path to secrets file or None if not found.
    """
    # Check project root first
    project_root = Path(__file__).parent.parent.parent
    project_secrets = project_root / "secrets.json"
    if project_secrets.exists():
        return project_secrets

    # Check home directory
    home_secrets = Path.home() / ".seedling" / "secrets.json"
    if home_secrets.exists():
        return home_secrets

    return None


class Config:
    """Configuration management for Seedling."""

    def __init__(self, secrets_path: Path | None = None) -> None:
        """Initialize configuration.

        Args:
            secrets_path: Optional path to secrets.json. Auto-detects if None.
        """
        if secrets_path is None:
            secrets_path = find_secrets_file()

        self.secrets_path = secrets_path
        self._secrets: Secrets | None = None

    def load_secrets(self) -> Secrets:
        """Load secrets from secrets.json.

        Returns:
            Secrets dict with all API keys.

        Raises:
            FileNotFoundError: If secrets.json doesn't exist.
            KeyError: If a required key is missing.
        """
        if self._secrets is not None:
            return self._secrets

        if self.secrets_path is None or not self.secrets_path.exists():
            raise FileNotFoundError(
                f"secrets.json not found.\n"
                f"Create it at:\n"
                f"  - ./secrets.json (project root), or\n"
                f"  - ~/.seedling/secrets.json"
            )

        with open(self.secrets_path, "r") as f:
            secrets = json.load(f)

        # Validate required keys
        required_keys = [
            "OPENROUTER_API_KEY",
            "JSEARCH_API_KEY",
            "R2_ACCOUNT_ID",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET",
            "ZEPHYR_URL",
            "ZEPHYR_API_KEY",
            "SEEDLING_EMAIL",
        ]

        missing = [k for k in required_keys if not secrets.get(k)]
        if missing:
            raise KeyError(f"Missing required secrets: {missing}")

        self._secrets = Secrets(
            OPENROUTER_API_KEY=secrets["OPENROUTER_API_KEY"],
            JSEARCH_API_KEY=secrets["JSEARCH_API_KEY"],
            EXA_API_KEY=secrets.get("EXA_API_KEY", ""),
            TAVILY_API_KEY=secrets.get("TAVILY_API_KEY", ""),
            R2_ACCOUNT_ID=secrets["R2_ACCOUNT_ID"],
            R2_ACCESS_KEY_ID=secrets["R2_ACCESS_KEY_ID"],
            R2_SECRET_ACCESS_KEY=secrets["R2_SECRET_ACCESS_KEY"],
            R2_BUCKET=secrets["R2_BUCKET"],
            R2_WORKER_URL=secrets.get("R2_WORKER_URL", ""),
            ZEPHYR_URL=secrets["ZEPHYR_URL"],
            ZEPHYR_API_KEY=secrets["ZEPHYR_API_KEY"],
            SEEDLING_EMAIL=secrets["SEEDLING_EMAIL"],
        )

        return self._secrets

    def get(self, key: str, default: Any = None) -> Any:
        """Get a secret value.

        Args:
            key: Secret key name.
            default: Default value if key not found.

        Returns:
            Secret value or default.
        """
        secrets = self.load_secrets()
        return secrets.get(key, default)


def load_secrets(secrets_path: Path | None = None) -> Secrets:
    """Load secrets from JSON file.

    Convenience function for loading secrets.

    Args:
        secrets_path: Optional path to secrets.json. Auto-detects if None.

    Returns:
        Secrets dict.
    """
    config = Config(secrets_path)
    return config.load_secrets()
