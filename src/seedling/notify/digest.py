"""Notification module using Zephyr Worker for email delivery."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader


@dataclass
class DigestJob:
    """Represents a qualified job for the digest."""

    id: str
    title: str
    company: str | None
    location: str | None
    match_score: int
    score_summary: str
    category: str
    url: str
    resume_url: str | None
    cover_letter_url: str | None
    cover_letter_requested: bool


@dataclass
class DigestStats:
    """Statistics for the digest."""

    total_discovered: int
    total_extracted: int
    total_rejected: int
    total_qualified: int
    tech_count: int
    serving_count: int


class DigestEmailBuilder:
    """Builds HTML digest emails."""

    def __init__(
        self,
        templates_dir: Path | None = None,
    ) -> None:
        """Initialize the digest builder.

        Args:
            templates_dir: Directory containing email templates.
        """
        # templates/ is at project root: digest.py -> notify/ -> seedling/ -> src/ -> project root
        self.templates_dir = (
            templates_dir or Path(__file__).parent.parent.parent.parent / "templates"
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

    def build_digest(
        self,
        jobs: list[DigestJob],
        stats: DigestStats,
        rejected_summary: str,
    ) -> str:
        """Build the HTML digest email.

        Args:
            jobs: List of qualified jobs.
            stats: Digest statistics.
            rejected_summary: Summary of rejected jobs.

        Returns:
            HTML content for the email.
        """
        template = self.jinja_env.get_template("digest-email.html")

        # Separate tech and serving jobs
        tech_jobs = [j for j in jobs if j.category.startswith("tech")]
        serving_jobs = [j for j in jobs if j.category == "serving"]

        # Generate date string
        date_str = datetime.now().strftime("%b %d")

        return template.render(
            date=date_str,
            total_jobs=len(jobs),
            tech_jobs=tech_jobs,
            serving_jobs=serving_jobs,
            stats=stats,
            rejected_summary=rejected_summary,
        )

    def build_plain_text(self, digest_html: str) -> str:
        """Generate plain text version from HTML.

        Args:
            digest_html: HTML content.

        Returns:
            Plain text version.
        """
        import re

        text = digest_html
        # Convert block elements to line breaks before stripping tags
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</p>", "\n\n", text)
        text = re.sub(r"</li>", "\n", text)
        text = re.sub(r"</h[1-6]>", "\n\n", text)
        text = re.sub(r"</div>", "\n", text)
        text = re.sub(r"</tr>", "\n", text)
        # Strip remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        # Collapse excessive whitespace but preserve intentional line breaks
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class ZephyrClient:
    """Client for the Zephyr email Worker."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the Zephyr client.

        Args:
            base_url: Zephyr Worker URL.
            api_key: Zephyr API key.
            http_client: Optional HTTP client.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, http2=True)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ZephyrClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> dict[str, Any]:
        """Send an email via Zephyr.

        Args:
            to: Recipient email.
            subject: Email subject.
            html: HTML email body.
            text: Optional plain text body.

        Returns:
            Response dict with success status and any error.
        """
        client = await self._get_client()

        payload = {
            "to": to,
            "subject": subject,
            "html": html,
        }

        if text:
            payload["text"] = text

        try:
            response = await client.post(
                f"{self.base_url}/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": str(e),
            }


async def send_digest(
    jobs: list[DigestJob],
    stats: DigestStats,
    rejected_summary: str,
    zephyr_url: str,
    zephyr_api_key: str,
    to_email: str,
) -> bool:
    """Send the job digest email.

    Args:
        jobs: List of qualified jobs.
        stats: Digest statistics.
        rejected_summary: Summary of rejected jobs.
        zephyr_url: Zephyr Worker URL.
        zephyr_api_key: Zephyr API key.
        to_email: Recipient email.

    Returns:
        True if email was sent successfully.
    """
    # Build the digest
    builder = DigestEmailBuilder()
    html = builder.build_digest(jobs, stats, rejected_summary)
    text = builder.build_plain_text(html)

    # Calculate subject
    tech_count = sum(1 for j in jobs if j.category.startswith("tech"))
    serving_count = len(jobs) - tech_count

    date_str = datetime.now().strftime("%b %d")
    subject = f"🌱 Seedling: {len(jobs)} matches found — {tech_count} tech, {serving_count} serving | {date_str}"

    # Send via Zephyr
    async with ZephyrClient(
        base_url=zephyr_url,
        api_key=zephyr_api_key,
    ) as client:
        result = await client.send_email(
            to=to_email,
            subject=subject,
            html=html,
            text=text,
        )

    return result.get("success", False)


def create_digest_jobs_from_db_jobs(db_jobs: list) -> list[DigestJob]:
    """Convert database jobs to DigestJob instances.

    Args:
        db_jobs: Database job records.

    Returns:
        List of DigestJob instances.
    """
    jobs = []
    for job in db_jobs:
        jobs.append(DigestJob(
            id=job.id,
            title=job.title or "Unknown",
            company=job.company,
            location=job.location,
            match_score=job.match_score or 0,
            score_summary=job.score_summary or "",
            category=job.category or "tech-devops",
            url=job.url,
            resume_url=job.resume_r2_url,
            cover_letter_url=job.cover_letter_r2_url,
            cover_letter_requested=job.cover_letter_requested,
        ))
    return jobs
