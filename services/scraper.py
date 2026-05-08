"""
services/scraper.py
===================
Job-description web scraper for the career-agent-email-cover project.

Technology choices
------------------
* ``requests`` for HTTP — lightweight, no browser overhead.
* ``BeautifulSoup`` (html.parser) for DOM parsing — no external binary needed.
* Explicitly NO Selenium / Playwright — this runs headlessly in GitHub Actions
  where a browser would add ~500 MB to the runner image and slow the workflow.

Limitations
-----------
* Cannot scrape JavaScript-rendered pages (React/Vue SPAs).
  For those sites, pre-fill the ``description`` column in the spreadsheet.
* Some job boards (LinkedIn, Indeed) block bots — again, use the sheet column.

Usage
-----
    from services.scraper import ScraperService
    from services.config import get_config

    svc = ScraperService(get_config())
    text = svc.fetch_job_description("https://example.com/jobs/123")
"""
from __future__ import annotations

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from services.config import Config
from services.logger import setup_logger

logger = setup_logger(__name__)

# Realistic browser headers to reduce the chance of being blocked by basic bot-detection
_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Tags that never contain useful job-description text
_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]

# Cap extracted text to avoid sending excessive tokens to OpenAI
_MAX_CHARS = 8_000


class ScraperService:
    """
    Fetches and cleans job descriptions from public job-posting URLs.

    The scraper tries several heuristics to locate the main content block
    (article, main, id/class containing "job"/"description"/"posting") before
    falling back to the full page body.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    def fetch_job_description(self, url: str) -> Optional[str]:
        """
        Download a job-posting page and extract clean readable text.

        Retries on network errors with exponential backoff.  Returns None
        (rather than raising) so the caller can fall back gracefully.

        Parameters
        ----------
        url:
            Full URL of the job posting.

        Returns
        -------
        str or None
            Cleaned text (≤ 8 000 chars), or None if all attempts fail.
        """
        retries = self.config.scrape_retries

        for attempt in range(retries):
            try:
                response = requests.get(
                    url,
                    headers=_HEADERS,
                    timeout=self.config.scrape_timeout,
                )
                response.raise_for_status()

                text = self._extract_text(response.text)
                if text:
                    logger.info(f"Scraped {len(text)} chars from: {url}")
                    return text

                logger.warning(f"Scrape returned empty content from: {url}")
                return None

            except requests.RequestException as exc:
                if attempt < retries - 1:
                    wait = 2 ** attempt  # 1 s, 2 s
                    logger.warning(
                        f"Scrape failed (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait}s: {exc}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Scrape failed for '{url}' after {retries} attempts: {exc}"
                    )
                    return None

        return None

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _extract_text(self, html: str) -> str:
        """
        Parse HTML and return clean plain text from the most content-rich element.

        Strategy
        --------
        1. Remove all noise tags (scripts, styles, navigation, etc.).
        2. Try to locate a specific job-content container via common selectors.
        3. Fall back to <body> if no container is found.
        4. Normalise whitespace and cap length.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Step 1 — strip noise tags in-place
        for tag in soup(_NOISE_TAGS):
            tag.decompose()

        # Step 2 — try progressively broader selectors to find the content block
        #          Patterns cover common job-board markup conventions.
        candidates = [
            soup.find("article"),
            soup.find("main"),
            soup.find(id=re.compile(r"job|description|posting|content", re.I)),
            soup.find(class_=re.compile(r"job|description|posting|content|detail", re.I)),
        ]

        # Use the first non-None match; fall back to body or root soup
        target = next((c for c in candidates if c is not None), None)
        if target is None:
            target = soup.body or soup

        # Step 3 — extract all visible text with spaces between elements
        raw_text = target.get_text(separator=" ")

        # Step 4 — normalise whitespace (collapse runs of spaces/newlines)
        clean_text = re.sub(r"\s+", " ", raw_text).strip()

        # Cap to _MAX_CHARS to prevent excessive OpenAI token spend
        return clean_text[:_MAX_CHARS]
