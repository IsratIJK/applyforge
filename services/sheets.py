"""
services/sheets.py
==================
Google Sheets integration for the career-agent-email-cover project.

Responsibilities
----------------
* Authenticate with Google Sheets API using a service-account JSON secret.
* Read all rows and return those whose ``status`` matches an allowed value.
* Update individual row status cells with exponential-backoff retry.

Expected spreadsheet columns (order-independent, matched by header name):
    status | company | role | job_id | link | description | resume_type

Usage
-----
    from services.sheets import SheetsService
    from services.config import get_config

    svc = SheetsService(get_config())
    jobs = svc.get_pending_jobs()
    svc.update_status(row_index=3, status="processing")
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

from services.config import Config
from services.logger import setup_logger

# OAuth scopes required for read + write access to Sheets (and Drive for auth)
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

logger = setup_logger(__name__)


@dataclass
class JobRow:
    """
    Immutable data transfer object representing one spreadsheet row.

    Attributes
    ----------
    row_index:
        1-based row index in the sheet (row 1 = header, row 2 = first data row).
        Used to call update_cell() without re-fetching the entire sheet.
    status:
        Raw status string from the sheet (e.g. "not applied").
    company:
        Hiring company name.
    role:
        Job title / role being applied for.
    job_id:
        Unique identifier for the posting (used in output file names).
    link:
        URL of the job posting — scraped when ``description`` is empty.
    description:
        Optional pre-filled job description.  When None the scraper fetches it.
    resume_type:
        Key that maps to an optimized resume profile in resumes/ (e.g. "backend").
    """

    row_index: int
    status: str
    company: str
    role: str
    job_id: str
    link: str
    description: Optional[str]
    resume_type: str


class SheetsService:
    """
    Thin wrapper around the gspread client for this project's specific needs.

    The service authenticates lazily on first use so that import-time errors
    (e.g. bad JSON) surface during the actual operation, not at module load.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._client: Optional[gspread.Client] = None
        self._sheet: Optional[gspread.Worksheet] = None

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #

    def _build_credentials(self) -> Credentials:
        """
        Parse the GOOGLE_SERVICE_ACCOUNT secret and return OAuth2 credentials.

        The secret is a full service-account JSON stored as a single string
        (never as a file on disk) so it is safe to pass via GitHub Secrets.
        """
        sa_info = json.loads(self.config.google_service_account)
        return Credentials.from_service_account_info(sa_info, scopes=_SCOPES)

    def connect(self) -> None:
        """Open the configured spreadsheet and cache the first worksheet."""
        creds = self._build_credentials()
        self._client = gspread.authorize(creds)
        spreadsheet = self._client.open(self.config.google_sheet_name)
        # Always work on the first (leftmost) sheet
        self._sheet = spreadsheet.sheet1
        logger.info(f"Connected to Google Sheet: '{self.config.google_sheet_name}'")

    def _ensure_connected(self) -> None:
        """Connect on first use (lazy initialisation pattern)."""
        if self._sheet is None:
            self.connect()

    # ------------------------------------------------------------------ #
    # Read operations                                                      #
    # ------------------------------------------------------------------ #

    def get_pending_jobs(self) -> list[JobRow]:
        """
        Fetch all rows whose status is in ``config.allowed_statuses``.

        Returns
        -------
        list[JobRow]
            At most ``config.max_jobs_per_run`` rows, preserving sheet order.
        """
        self._ensure_connected()

        # get_all_records() returns a list of dicts keyed by the header row
        records = self._sheet.get_all_records()
        jobs: list[JobRow] = []

        for i, record in enumerate(records, start=2):  # row 2 = first data row (header is row 1)
            raw_status = str(record.get("status", "")).strip().lower()
            allowed = [s.lower() for s in self.config.allowed_statuses]

            if raw_status not in allowed:
                continue

            jobs.append(
                JobRow(
                    row_index=i,
                    status=str(record.get("status", "")).strip(),
                    company=str(record.get("company", "")).strip(),
                    role=str(record.get("role", "")).strip(),
                    job_id=str(record.get("job_id", "")).strip(),
                    link=str(record.get("link", "")).strip(),
                    # Treat empty string as absent description
                    description=str(record.get("description", "")).strip() or None,
                    resume_type=str(record.get("resume_type", "default")).strip().lower() or "default",
                )
            )

        logger.info(f"Found {len(jobs)} pending job(s) in sheet")

        # Honour the per-run cap to avoid runaway API spend
        return jobs[: self.config.max_jobs_per_run]

    # ------------------------------------------------------------------ #
    # Write operations                                                     #
    # ------------------------------------------------------------------ #

    def update_status(self, row_index: int, status: str) -> None:
        """
        Write a new status value to the ``status`` column of a specific row.

        Uses exponential backoff (1 s, 2 s, 4 s …) on Sheets API errors.

        Parameters
        ----------
        row_index:
            1-based row number (as stored in JobRow.row_index).
        status:
            New status string, e.g. "processing" or "draft generated".
        """
        self._ensure_connected()

        # Locate the status column dynamically so column order doesn't matter
        header = self._sheet.row_values(1)
        try:
            status_col = header.index("status") + 1  # gspread uses 1-based column indices
        except ValueError:
            logger.error("Column 'status' not found in sheet header row — cannot update")
            return

        retries = self.config.google_retries
        for attempt in range(retries):
            try:
                self._sheet.update_cell(row_index, status_col, status)
                logger.info(f"Row {row_index} → status='{status}'")
                return
            except APIError as exc:
                if attempt < retries - 1:
                    wait = 2 ** attempt  # 1 s, 2 s, 4 s
                    logger.warning(
                        f"Sheets API error on update (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait}s: {exc}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Failed to update row {row_index} after {retries} attempts: {exc}"
                    )
                    raise
