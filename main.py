"""
main.py
=======
Career Agent — Automated Email & Cover Letter Generator

Entry point for the daily GitHub Actions workflow.

Automation flow
---------------
1.  Load configuration and validate required secrets.
2.  Connect to Google Sheets and fetch rows with status "not applied".
3.  For each job (up to MAX_JOBS_PER_RUN):
    a.  Mark row as "processing".
    b.  Scrape job description from the link if none is in the sheet.
    c.  Load the matching optimized resume profile from resumes/.
    d.  Generate a cover letter and recruiter email via OpenAI.
    e.  Save outputs as .md (both) and .docx (cover letter).
    f.  Upload all generated files to Google Drive under Applications/<Company>/.
    g.  Mark row as "draft generated".
4.  On any per-job failure: mark as "failed", log the error, continue.
5.  Log a final summary of successes and failures.

Environment
-----------
All configuration is read from environment variables (see example.env).
Local development: copy example.env → .env and fill in values.
CI/CD: set via GitHub Actions Secrets and Variables.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing services so env vars are available at import time
load_dotenv(Path(__file__).parent / ".env")

from services.config import get_config
from services.document_generator import build_output_paths, save_docx, save_markdown
from services.drive import DriveService
from services.logger import setup_logger
from services.openai_client import OpenAIClient
from services.prompts import (
    COVER_LETTER_SYSTEM,
    COVER_LETTER_USER,
    RECRUITER_EMAIL_SYSTEM,
    RECRUITER_EMAIL_USER,
)
from services.resume_optimizer import load_resume_profile
from services.scraper import ScraperService
from services.sheets import JobRow, SheetsService


# ======================================================================== #
# Per-job processing                                                         #
# ======================================================================== #

def process_job(
    job: JobRow,
    config,
    sheets: SheetsService,
    drive: DriveService,
    openai: OpenAIClient,
    scraper: ScraperService,
    logger,
) -> None:
    """
    Process a single job application end-to-end.

    Marks the row "processing" at the start and "draft generated" on success.
    Raises on failure so the caller can mark the row "failed" and continue.

    Parameters
    ----------
    job:
        Data from one spreadsheet row.
    config:
        Project configuration singleton.
    sheets, drive, openai, scraper:
        Initialized service instances (injected for testability).
    logger:
        Named logger from the calling context.
    """
    logger.info(
        f"--- Processing: {job.company} | {job.role} | ID: {job.job_id or 'N/A'} ---"
    )

    # ---- Step 1: Mark as processing so concurrent runs skip this row ----
    sheets.update_status(job.row_index, config.status_processing)

    # ---- Step 2: Resolve job description ----
    job_description = job.description

    if not job_description:
        if not job.link:
            logger.warning(
                f"Row {job.row_index}: no description and no link — "
                f"using minimal fallback context"
            )
            job_description = f"Role: {job.role} at {job.company}."
        else:
            logger.info(f"Description missing — scraping: {job.link}")
            job_description = scraper.fetch_job_description(job.link)

            if not job_description:
                # Scrape failed — use a minimal stub so generation still runs
                logger.warning(
                    f"Scrape failed for {job.company} — using fallback description"
                )
                job_description = (
                    f"Role: {job.role} at {job.company}. "
                    f"See full details at: {job.link}"
                )

    # ---- Step 3: Load optimized resume profile ----
    # Truncating is not needed here — optimized profiles are already compact
    resume_profile = load_resume_profile(config.resumes_dir, job.resume_type)

    # ---- Step 4: Generate cover letter via OpenAI ----
    logger.info("Generating cover letter...")
    cover_letter = openai.generate(
        system_prompt=COVER_LETTER_SYSTEM,
        user_prompt=COVER_LETTER_USER.format(
            resume_profile=resume_profile,
            company=job.company,
            role=job.role,
            # Cap JD to 4 000 chars to stay within a sensible context budget
            job_description=job_description[:4_000],
        ),
        max_tokens=600,
    )

    # ---- Step 5: Generate recruiter email via OpenAI ----
    logger.info("Generating recruiter email...")
    recruiter_email = openai.generate(
        system_prompt=RECRUITER_EMAIL_SYSTEM,
        user_prompt=RECRUITER_EMAIL_USER.format(
            resume_profile=resume_profile,
            company=job.company,
            role=job.role,
            # Slightly shorter cap for the email — it needs less JD context
            job_description=job_description[:3_000],
        ),
        max_tokens=400,
    )

    # ---- Step 6: Build output file paths ----
    paths = build_output_paths(config.output_dir, job.company, job.job_id)

    # ---- Step 7: Save files ----
    # Recruiter email: Markdown only (easy to paste into Gmail / Outlook)
    email_md_content = (
        f"# Recruiter Email — {job.company}\n"
        f"**Role:** {job.role}  \n"
        f"**Job ID:** {job.job_id or 'N/A'}  \n"
        f"**Link:** {job.link or 'N/A'}\n\n"
        f"---\n\n"
        f"{recruiter_email}"
    )
    save_markdown(email_md_content, paths["email_md"])

    # Cover letter: both Markdown and DOCX
    cover_md_content = (
        f"# Cover Letter — {job.company}\n"
        f"**Role:** {job.role}  \n"
        f"**Job ID:** {job.job_id or 'N/A'}  \n"
        f"**Link:** {job.link or 'N/A'}\n\n"
        f"---\n\n"
        f"{cover_letter}"
    )
    save_markdown(cover_md_content, paths["cover_letter_md"])
    save_docx(
        content=cover_letter,
        file_path=paths["cover_letter_docx"],
        title=f"Cover Letter — {job.role} at {job.company}",
    )

    # ---- Step 8: Upload to Google Drive ----
    logger.info(f"Uploading files to Drive → Applications/{job.company}/")
    for key in ("email_md", "cover_letter_md", "cover_letter_docx"):
        drive.upload_file(paths[key], company_name=job.company)

    # ---- Step 9: Mark as done ----
    sheets.update_status(job.row_index, config.status_draft_generated)
    logger.info(f"Done: {job.company} | {job.role}")


# ======================================================================== #
# Entry point                                                                #
# ======================================================================== #

def main() -> None:
    """
    Main automation entry point.

    Orchestrates the full workflow:
    fetch → process each job → handle failures → summarize.
    """
    config = get_config()

    # Validate required secrets early — fail fast with a clear message
    try:
        config.validate()
    except ValueError as exc:
        print(f"[FATAL] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger("main", log_level=config.log_level, logs_dir=config.logs_dir)
    logger.info("=" * 60)
    logger.info("Career Agent starting")
    logger.info(f"Model: {config.openai_model} | Max jobs: {config.max_jobs_per_run}")
    logger.info("=" * 60)

    # ---- Initialize services ----
    sheets = SheetsService(config)
    drive = DriveService(config)
    openai = OpenAIClient(config)
    scraper = ScraperService(config)

    # ---- Fetch pending jobs ----
    try:
        pending_jobs = sheets.get_pending_jobs()
    except Exception as exc:
        logger.error(f"Failed to fetch jobs from Google Sheets: {exc}", exc_info=True)
        sys.exit(1)

    if not pending_jobs:
        logger.info("No pending jobs found — exiting cleanly")
        return

    logger.info(f"Processing {len(pending_jobs)} job(s)")

    # ---- Process each job ----
    succeeded = 0
    failed = 0

    for job in pending_jobs:
        try:
            process_job(job, config, sheets, drive, openai, scraper, logger)
            succeeded += 1
        except Exception as exc:
            logger.error(
                f"Job failed [{job.company} | {job.role}]: {exc}",
                exc_info=True,
            )
            # Best-effort status update — don't let a secondary failure mask the primary one
            try:
                sheets.update_status(job.row_index, config.status_failed)
            except Exception as update_exc:
                logger.warning(f"Could not mark row {job.row_index} as failed: {update_exc}")
            failed += 1

        # Rate limit: pause between jobs to reduce burst API pressure
        if pending_jobs.index(job) < len(pending_jobs) - 1:
            time.sleep(config.rate_limit_delay)

    # ---- Final summary ----
    logger.info("=" * 60)
    logger.info(
        f"Run complete | Succeeded: {succeeded} | Failed: {failed} | "
        f"Total: {len(pending_jobs)}"
    )
    logger.info("=" * 60)

    # Exit with non-zero code if any job failed (useful for GitHub Actions alerts)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
