"""Playwright backup discovery for JavaScript-rendered pages."""

from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx


@dataclass
class PlaywrightJob:
    """Represents a job discovered via Playwright."""

    url: str
    title: str
    company: str | None
    location: str | None
    description: str


class PlaywrightDiscovery:
    """Backup discovery using Playwright for JS-rendered pages."""

    def __init__(self) -> None:
        """Initialize the Playwright discovery module."""
        self._browser = None

    async def close(self) -> None:
        """Close the browser if open."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None

    async def __aenter__(self) -> "PlaywrightDiscovery":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def discover_from_url(
        self, url: str, wait_for_selector: str = ".jobsearch-jobDescriptionText"
    ) -> Optional[PlaywrightJob]:
        """Scrape a job page using Playwright.

        This is a backup for pages that require JavaScript rendering.

        Args:
            url: URL to scrape.
            wait_for_selector: CSS selector to wait for.

        Returns:
            PlaywrightJob or None if extraction fails.
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await page.wait_for_selector(
                        wait_for_selector, timeout=10000
                    )

                    # Extract job info
                    title = await page.title()

                    # Get job description
                    description_el = await page.query_selector(
                        ".jobsearch-jobDescriptionText"
                    )
                    description = (
                        await description_el.inner_text()
                        if description_el
                        else ""
                    )

                    return PlaywrightJob(
                        url=url,
                        title=title,
                        company=None,
                        location=None,
                        description=description[:2000],
                    )

                finally:
                    await browser.close()

        except ImportError:
            print("   ⚠️ Playwright not installed. Run: uv run playwright install")
            return None
        except Exception as e:
            print(f"   ⚠️ Playwright scraping failed for {url}: {e}")
            return None


async def scrape_job_page(
    url: str,
) -> Optional[PlaywrightJob]:
    """Scrape a single job page using Playwright.

    Args:
        url: URL to scrape.

    Returns:
        PlaywrightJob or None.
    """
    async with PlaywrightDiscovery() as discovery:
        return await discovery.discover_from_url(url)
