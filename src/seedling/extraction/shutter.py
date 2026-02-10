"""Extraction module using Shutter (local UV tool).

Shutter is installed via: uv tool install --editable /Users/autumn/Documents/Projects/Shutter
"""

import asyncio
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ExtractedJob:
    """Represents extracted job details from Shutter."""

    url: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    salary_text: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    preferred: Optional[str] = None
    posting_date: Optional[str] = None
    application_method: Optional[str] = None
    pi_detected: bool = False
    raw_output: Optional[str] = None


def find_shutter_executable() -> Optional[Path]:
    """Find the Shutter executable.

    Returns:
        Path to shutter executable or None if not found.
    """
    # Check if shutter is in PATH
    shutter_path = shutil.which("shutter")
    if shutter_path:
        return Path(shutter_path)

    # Check common locations
    common_paths = [
        Path.home() / ".local" / "bin" / "shutter",
        Path("/usr/local/bin/shutter"),
        Path("/usr/bin/shutter"),
    ]

    for path in common_paths:
        if path.exists():
            return path

    return None


def extract_with_shutter(
    url: str,
    query: str,
    model: str = "accurate",
    max_tokens: int = 500,
    timeout_ms: int = 30000,
) -> ExtractedJob:
    """Extract job details using Shutter.

    Args:
        url: Job listing URL to extract.
        query: Query describing what to extract.
        model: Model tier (fast, accurate, research, code).
        max_tokens: Maximum output tokens.
        timeout_ms: Timeout in milliseconds.

    Returns:
        ExtractedJob with extracted details.
    """
    shutter_path = find_shutter_executable()

    if shutter_path is None:
        raise RuntimeError(
            "Shutter not found. Install with: "
            "uv tool install --editable /Users/autumn/Documents/Projects/Shutter"
        )

    # Build command
    cmd = [
        str(shutter_path),
        url,
        "--query", query,
        "--model", model,
        "--max-tokens", str(max_tokens),
        "--timeout", str(timeout_ms),
    ]

    # Run shutter
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_ms / 1000 + 60,  # Add 60s buffer
    )

    if result.returncode != 0:
        raise RuntimeError(f"Shutter failed: {result.stderr}")

    # Parse output
    try:
        output = json.loads(result.stdout)
        return _parse_shutter_output(url, output)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Shutter output: {e}\n{result.stdout}")


async def extract_with_shutter_async(
    url: str,
    query: str,
    model: str = "accurate",
    max_tokens: int = 500,
    timeout_ms: int = 30000,
) -> ExtractedJob:
    """Extract job details using Shutter asynchronously.

    Args:
        url: Job listing URL to extract.
        query: Query describing what to extract.
        model: Model tier (fast, accurate, research, code).
        max_tokens: Maximum output tokens.
        timeout_ms: Timeout in milliseconds.

    Returns:
        ExtractedJob with extracted details.
    """
    shutter_path = find_shutter_executable()

    if shutter_path is None:
        raise RuntimeError(
            "Shutter not found. Install with: "
            "uv tool install --editable /Users/autumn/Documents/Projects/Shutter"
        )

    # Build command
    cmd = [
        str(shutter_path),
        url,
        "--query", query,
        "--model", model,
        "--max-tokens", str(max_tokens),
        "--timeout", str(timeout_ms),
    ]

    # Run shutter asynchronously
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_ms / 1000 + 60,
        )
    except asyncio.TimeoutError:
        process.kill()
        raise RuntimeError(f"Shutter timed out for {url}")

    if process.returncode != 0:
        error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
        raise RuntimeError(f"Shutter failed: {error_msg}")

    # Parse output
    try:
        output = json.loads(stdout.decode("utf-8"))
        return _parse_shutter_output(url, output)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse Shutter output: {e}\n{stdout.decode('utf-8')}"
        )


def _parse_shutter_output(url: str, output: dict) -> ExtractedJob:
    """Parse Shutter JSON output into ExtractedJob.

    Args:
        url: Original URL.
        output: Shutter JSON output.

    Returns:
        ExtractedJob instance.
    """
    # Extract text from Shutter response
    # Shutter returns "extracted" (not "text") and nested "prompt_injection" object
    extracted_text = output.get("extracted", "")
    pi_info = output.get("prompt_injection", {})
    pi_detected = pi_info.get("detected", False) if isinstance(pi_info, dict) else False

    # Try to parse structured fields from the text
    # Shutter returns plain text, we need to parse it
    title = _extract_field(extracted_text, "title")
    company = _extract_field(extracted_text, "company")
    location = _extract_field(extracted_text, "location")
    salary_text = _extract_field(extracted_text, "salary")

    # Parse salary range
    salary_min, salary_max = _parse_salary(salary_text)

    description = extracted_text

    return ExtractedJob(
        url=url,
        title=title,
        company=company,
        location=location,
        remote=_is_remote(location),
        salary_text=salary_text,
        salary_min=salary_min,
        salary_max=salary_max,
        description=description,
        requirements=None,
        preferred=None,
        posting_date=None,
        application_method=None,
        pi_detected=pi_detected,
        raw_output=json.dumps(output),
    )


def _extract_field(text: str, field: str) -> Optional[str]:
    """Extract a field from Shutter output text.

    Args:
        text: Shutter output text.
        field: Field name to extract.

    Returns:
        Field value or None.
    """
    # Look for patterns like "Title: ..." or "Company: ..."
    patterns = [
        f"{field}:",
        f"{field.title()}:",
    ]

    for pattern in patterns:
        idx = text.lower().find(pattern.lower())
        if idx != -1:
            # Extract the rest of the line
            start = idx + len(pattern)
            end = text.find("\n", start)
            if end == -1:
                end = len(text)
            value = text[start:end].strip()
            return value if value else None

    return None


def _parse_salary(salary_text: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Parse salary text into min/max values.

    Args:
        salary_text: Salary string like "$80,000 - $120,000".

    Returns:
        Tuple of (min, max) or (None, None).
    """
    if not salary_text:
        return None, None

    import re

    # Find all dollar amounts
    amounts = re.findall(r"\$?([\d,]+)", salary_text)
    amounts = [int(a.replace(",", "")) for a in amounts if a]

    if not amounts:
        return None, None

    if len(amounts) == 1:
        return amounts[0], amounts[0]

    return min(amounts), max(amounts)


def _is_remote(location: Optional[str]) -> Optional[bool]:
    """Check if location indicates remote work.

    Args:
        location: Location string.

    Returns:
        True if remote, False if not, None if unknown.
    """
    if not location:
        return None

    location_lower = location.lower()
    if "remote" in location_lower:
        return True
    if "onsite" in location_lower or "in-person" in location_lower:
        return False

    return None


# Default extraction query for job listings
DEFAULT_JOB_QUERY = """
Extract the following from this job listing:
- Job title
- Company name
- Location (remote/onsite/hybrid)
- Salary range (if listed)
- Full job description
- Required qualifications
- Preferred qualifications
- Posting date
- Application method
"""


def extract_job(
    url: str,
    query: str = DEFAULT_JOB_QUERY,
    model: str = "accurate",
) -> ExtractedJob:
    """Extract job details from a URL.

    Convenience function for extracting a single job.

    Args:
        url: Job listing URL.
        query: Custom extraction query.
        model: Model tier.

    Returns:
        ExtractedJob instance.
    """
    return extract_with_shutter(
        url=url,
        query=query,
        model=model,
        max_tokens=1000,
    )


async def extract_job_async(
    url: str,
    query: str = DEFAULT_JOB_QUERY,
    model: str = "accurate",
) -> ExtractedJob:
    """Extract job details from a URL asynchronously.

    Convenience function for extracting a single job.

    Args:
        url: Job listing URL.
        query: Custom extraction query.
        model: Model tier.

    Returns:
        ExtractedJob instance.
    """
    return await extract_with_shutter_async(
        url=url,
        query=query,
        model=model,
        max_tokens=1000,
    )
