# career-agent-email-cover

Automated daily job-application assistant.  Reads your job list from a Google
Spreadsheet, generates a personalized cover letter and recruiter email for each
opening using OpenAI, saves the files as `.md` and `.docx`, and uploads
everything to Google Drive — all without human intervention.

Runs every day at **1:00 AM Bangladesh Standard Time** via GitHub Actions.
Every configuration value is tunable through environment variables or GitHub
Actions Variables — no core code changes required.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Google Cloud Setup](#google-cloud-setup)
5. [Spreadsheet Setup](#spreadsheet-setup)
6. [Resume Preprocessing Pipeline](#resume-preprocessing-pipeline)
7. [Local Development Setup](#local-development-setup)
8. [GitHub Actions Setup](#github-actions-setup)
9. [Configuration Reference](#configuration-reference)
10. [Cron Schedule Customization](#cron-schedule-customization)
11. [OpenAI Cost Optimization](#openai-cost-optimization)
12. [Generated Output Structure](#generated-output-structure)
13. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Google Spreadsheet
    │
    ▼  (read rows where status = "not applied")
services/sheets.py
    │
    ├─► services/scraper.py          (fetch job description if missing)
    │
    ├─► services/resume_optimizer.py (load optimized .txt profile)
    │
    ├─► services/openai_client.py    (generate cover letter + email)
    │
    ├─► services/document_generator.py (.md + .docx output files)
    │
    └─► services/drive.py            (upload to Google Drive)
    │
    ▼  (update row status → "draft generated")
Google Spreadsheet
```

The automation runs once per day.  Each job row is processed independently —
one failure does not stop the rest.

---

## Project Structure

```
career-agent-email-cover/
│
├── .github/
│   └── workflows/
│       └── automation.yml      ← GitHub Actions daily workflow
│
├── services/                   ← Modular service layer
│   ├── __init__.py
│   ├── config.py               ← Centralized configuration (env vars)
│   ├── logger.py               ← Structured logging factory
│   ├── sheets.py               ← Google Sheets read/write
│   ├── drive.py                ← Google Drive folder + upload
│   ├── openai_client.py        ← OpenAI chat-completion with retry
│   ├── scraper.py              ← Job-page web scraper
│   ├── prompts.py              ← All AI prompt templates
│   ├── document_generator.py   ← .md and .docx file generation
│   └── resume_optimizer.py     ← PDF extraction + profile loading
│
├── scripts/
│   └── process_resume.py       ← One-time resume preprocessing script
│
├── raw_resumes/                ← Drop your PDF resumes here
│   └── .gitkeep
│
├── resumes/                    ← Optimized .txt profiles (auto-generated)
│   ├── .gitkeep
│   ├── backend.txt             ← Placeholder (replace via preprocessing)
│   ├── ai.txt                  ← Placeholder
│   └── default.txt             ← Fallback profile
│
├── output/                     ← Generated documents (gitignored)
│   └── .gitkeep
│
├── logs/                       ← Daily log files (gitignored)
│   └── .gitkeep
│
├── main.py                     ← Entry point for the automation
├── requirements.txt
├── example.env                 ← Environment variable reference
├── .gitignore
└── README.md
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Required |
| pip | latest | `pip install --upgrade pip` |
| Git | any | For cloning and GitHub Actions |
| Google Cloud account | free tier OK | For Sheets + Drive APIs |
| OpenAI account | paid | API key with billing enabled |

---

## Google Cloud Setup

### Step 1 — Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Click **Select a project** → **New Project**.
3. Name it (e.g. `career-agent`) and click **Create**.

### Step 2 — Enable APIs

In the project, enable both APIs:

**Google Sheets API:**
```
APIs & Services → Library → search "Google Sheets API" → Enable
```

**Google Drive API:**
```
APIs & Services → Library → search "Google Drive API" → Enable
```

### Step 3 — Create a Service Account

1. Go to **IAM & Admin → Service Accounts → Create Service Account**.
2. Name it (e.g. `career-agent-sa`).
3. Grant these roles:
   - **Editor** (or specifically: Sheets Editor + Drive File Creator)
4. Click **Done**.

### Step 4 — Create and Download a JSON Key

1. Click the service account you just created.
2. Go to the **Keys** tab → **Add Key → Create new key → JSON**.
3. The key file downloads automatically.
4. **Open the file**, copy its entire contents (the full JSON object).
5. This value goes into `GOOGLE_SERVICE_ACCOUNT` (see below).

> **Security note:** Never commit this JSON file. Always store it as a secret
> string in GitHub or in your local `.env` file.

### Step 5 — Share the Spreadsheet with the Service Account

1. Open your Google Spreadsheet.
2. Click **Share**.
3. Add the service account email (looks like `name@project.iam.gserviceaccount.com`).
4. Give it **Editor** access.
5. Click **Send**.

The service account must also have access to the target Google Drive folder,
or the automation will create the `Applications/` folder in the account's
own Drive (which it has access to by default).

---

## Spreadsheet Setup

Create a Google Spreadsheet with these exact column headers in row 1:

| status | company | role | job_id | link | description | resume_type |
|--------|---------|------|--------|------|-------------|-------------|

### Column descriptions

| Column | Required | Description |
|--------|----------|-------------|
| `status` | Yes | Workflow status (see values below) |
| `company` | Yes | Company name (used in file names and Drive folders) |
| `role` | Yes | Job title |
| `job_id` | No | Posting ID (used in output file names for uniqueness) |
| `link` | Yes* | Job posting URL — scraped if `description` is empty |
| `description` | No | Pre-filled job description (skips scraping) |
| `resume_type` | Yes | Key matching a profile in `resumes/` (e.g. `backend`, `ai`) |

### Status values

| Value | Meaning |
|-------|---------|
| `not applied` | Ready to process — picked up by the automation |
| `processing` | Currently being processed (set at start of each job) |
| `draft generated` | Email + cover letter generated and uploaded |
| `reviewed` | You reviewed and approved the draft |
| `applied` | Application submitted manually |
| `failed` | Processing failed — see logs for details |

### Example rows

| status | company | role | job_id | link | description | resume_type |
|--------|---------|------|--------|------|-------------|-------------|
| not applied | Stripe | Backend Engineer | JOB-001 | https://stripe.com/jobs/123 | | backend |
| not applied | OpenAI | ML Engineer | JOB-002 | https://openai.com/jobs/456 | | ai |
| not applied | Acme Corp | Full Stack Dev | JOB-003 | | We are looking for... | default |

---

## Resume Preprocessing Pipeline

The preprocessing pipeline converts your raw PDF resumes into compact,
token-efficient text profiles used at generation time.

### Why preprocess?

| Approach | Tokens per job | Cost per 100 jobs (approx) |
|----------|---------------|---------------------------|
| Raw PDF text (~1500 tokens) | ~2000 tokens total | ~$0.60 |
| Optimized profile (~400 tokens) | ~900 tokens total | ~$0.27 |

**Savings: ~55% per run.**  At scale this adds up significantly.

### Step 1 — Add your PDF resumes

Place your PDF resumes in the `raw_resumes/` directory.

Name each file to match the `resume_type` value you use in the spreadsheet:

```
raw_resumes/
    backend.pdf    →  resumes/backend.txt   (resume_type: backend)
    ai.pdf         →  resumes/ai.txt        (resume_type: ai)
    default.pdf    →  resumes/default.txt   (resume_type: default)
```

You can use any name — the output filename mirrors the PDF stem.

### Step 2 — Run the preprocessing script

```bash
python scripts/process_resume.py
```

The script will:
1. Read each PDF from `raw_resumes/`.
2. Extract text using PyMuPDF.
3. Call OpenAI to generate a structured, compressed profile.
4. Save the profile to `resumes/<name>.txt`.

### Step 3 — Review the output

Open the generated `.txt` files in `resumes/` and verify they contain:
- Professional summary
- Key technical skills (all relevant ones preserved)
- Experience highlights
- Notable projects
- Domain expertise

If a section is missing or inaccurate, you can edit the `.txt` file manually.

### Step 4 — Commit the profiles

```bash
git add resumes/
git commit -m "Add optimized resume profiles"
git push
```

Profiles are committed to the repo so GitHub Actions can access them without
re-running preprocessing on every workflow run.

> **Note:** The `.gitignore` excludes `resumes/*.txt` by default to protect
> personal information. Remove that rule if you want to commit your profiles.

---

## Local Development Setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/career-agent-email-cover.git
cd career-agent-email-cover
```

### Step 2 — Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
```

### Step 3 — Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

```bash
cp example.env .env
```

Edit `.env` and fill in:

```env
OPENAI_API_KEY=sk-...
GOOGLE_SERVICE_ACCOUNT={"type":"service_account","project_id":"..."}
GOOGLE_SHEET_NAME=Job Applications
GOOGLE_DRIVE_PARENT_FOLDER=Applications
```

### Step 5 — Preprocess resumes

```bash
# Place PDFs in raw_resumes/ first
python scripts/process_resume.py
```

### Step 6 — Run the automation locally

```bash
python main.py
```

---

## GitHub Actions Setup

### Step 1 — Push the repository to GitHub

```bash
git remote add origin https://github.com/your-username/career-agent-email-cover.git
git push -u origin main
```

### Step 2 — Add GitHub Secrets

Go to: **Repository → Settings → Secrets and variables → Actions → Secrets**

| Secret name | Value |
|-------------|-------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GOOGLE_SERVICE_ACCOUNT` | Full content of the service-account JSON key file |

Paste the entire JSON as a single value (including `{` and `}`).

### Step 3 — Add GitHub Variables (optional)

Go to: **Repository → Settings → Secrets and variables → Actions → Variables**

All of these have sensible defaults — only set them if you want to override:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_SHEET_NAME` | `Job Applications` | Exact spreadsheet name |
| `GOOGLE_DRIVE_PARENT_FOLDER` | `Applications` | Top-level Drive folder |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for generation |
| `OPENAI_TEMPERATURE` | `0.7` | Generation temperature |
| `MAX_JOBS_PER_RUN` | `10` | Per-run job cap |
| `RATE_LIMIT_DELAY` | `2` | Seconds between jobs |
| `REQUEST_TIMEOUT` | `20` | HTTP timeout (seconds) |
| `SCRAPE_TIMEOUT` | `30` | Scrape timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `OPENAI_RETRIES` | `3` | OpenAI retry count |
| `GOOGLE_RETRIES` | `3` | Google API retry count |
| `SCRAPE_RETRIES` | `2` | Scrape retry count |

### Step 4 — Verify the workflow

Go to **Actions → Career Agent Automation → Run workflow** to trigger a manual run
and confirm everything works before relying on the daily schedule.

---

## Configuration Reference

All configuration lives in `services/config.py` and is driven by environment
variables.  This table is the complete reference.

| Environment variable | Type | Default | Description |
|----------------------|------|---------|-------------|
| `OPENAI_API_KEY` | str | *(required)* | OpenAI API key |
| `GOOGLE_SERVICE_ACCOUNT` | str | *(required)* | Service-account JSON string |
| `GOOGLE_SHEET_NAME` | str | `Job Applications` | Spreadsheet name |
| `GOOGLE_DRIVE_PARENT_FOLDER` | str | `Applications` | Drive parent folder |
| `OPENAI_MODEL` | str | `gpt-4o-mini` | Generation model |
| `OPENAI_TEMPERATURE` | float | `0.7` | Generation temperature |
| `APP_TIMEZONE` | str | `Asia/Dhaka` | Timezone (informational) |
| `CRON_SCHEDULE` | str | `0 19 * * *` | Cron (informational; edit YAML) |
| `MAX_JOBS_PER_RUN` | int | `10` | Max rows processed per run |
| `RATE_LIMIT_DELAY` | float | `2` | Seconds sleep between jobs |
| `REQUEST_TIMEOUT` | int | `20` | HTTP request timeout (s) |
| `SCRAPE_TIMEOUT` | int | `30` | Scrape timeout (s) |
| `OPENAI_RETRIES` | int | `3` | OpenAI retry attempts |
| `GOOGLE_RETRIES` | int | `3` | Google API retry attempts |
| `SCRAPE_RETRIES` | int | `2` | Scrape retry attempts |
| `LOG_LEVEL` | str | `INFO` | Logging level |
| `OUTPUT_DIR` | str | `output` | Local output directory |
| `LOGS_DIR` | str | `logs` | Local logs directory |
| `RESUMES_DIR` | str | `resumes` | Optimized profiles directory |
| `RAW_RESUMES_DIR` | str | `raw_resumes` | Source PDF directory |

---

## Cron Schedule Customization

The schedule is defined in `.github/workflows/automation.yml`:

```yaml
on:
  schedule:
    - cron: "0 19 * * *"
```

GitHub Actions cron runs in **UTC**.  The table below shows common Bangladesh-
time targets and their UTC equivalents:

| Bangladesh Time (BST, UTC+6) | UTC cron expression |
|------------------------------|---------------------|
| 12:00 AM midnight | `0 18 * * *` |
| 1:00 AM | `0 19 * * *` ← default |
| 6:00 AM | `0 0 * * *` |
| 12:00 PM noon | `0 6 * * *` |
| 6:00 PM | `0 12 * * *` |
| 10:00 PM | `0 16 * * *` |

**Formula:** `BST hour - 6 = UTC hour` (if result is negative, add 24 and subtract 1 from the day).

To run only on weekdays:
```yaml
- cron: "0 19 * * 1-5"   # Monday–Friday at 1 AM BST
```

---

## OpenAI Cost Optimization

### Two-phase resume approach

Raw PDFs are processed **once** via `scripts/process_resume.py`.  The automation
uses only the compact `.txt` profiles — never the original PDFs.

| Stage | When | Token cost |
|-------|------|-----------|
| Resume preprocessing | Once per PDF update | ~1 200 tokens per resume |
| Per job (cover letter) | Each run | ~900 tokens |
| Per job (recruiter email) | Each run | ~550 tokens |
| **Total per job** | | **~1 450 tokens ≈ $0.0002** |

At `gpt-4o-mini` pricing, processing 10 jobs costs roughly **$0.002** per run.

### Additional cost controls

- `MAX_JOBS_PER_RUN` caps the number of API calls per workflow run.
- `max_tokens` is set conservatively per call (600 for cover letters, 400 for emails).
- Job descriptions are truncated to 4 000 chars before being sent to the API.
- `OPENAI_MODEL=gpt-4o-mini` is the default — upgrade to `gpt-4o` only if quality
  is insufficient for your needs.

---

## Generated Output Structure

```
output/
└── Stripe/
    ├── Stripe_JOB-001_recruiter_email.md
    ├── Stripe_JOB-001_cover_letter.md
    └── Stripe_JOB-001_cover_letter.docx

Google Drive:
Applications/
└── Stripe/
    ├── Stripe_JOB-001_recruiter_email.md
    ├── Stripe_JOB-001_cover_letter.md
    └── Stripe_JOB-001_cover_letter.docx
```

---

## Troubleshooting

### "GOOGLE_SERVICE_ACCOUNT is required"

The secret is missing or empty.  Check:
- Local: `.env` file has the full JSON value (not just the file path).
- GitHub Actions: the `GOOGLE_SERVICE_ACCOUNT` secret is set under
  **Settings → Secrets and variables → Actions → Secrets**.

### "SpreadsheetNotFound" error

- The spreadsheet name in `GOOGLE_SHEET_NAME` must match **exactly** (case-sensitive).
- The service account email must have **Editor** access to the spreadsheet.

### "FileNotFoundError: No resume profile found for type 'backend'"

Run the preprocessing script first:
```bash
python scripts/process_resume.py
```
And make sure `resumes/backend.txt` exists and is non-empty.

### Scraping returns empty or fails

Some job boards (LinkedIn, Indeed, Greenhouse) block automated requests.
Solutions:
1. Pre-fill the `description` column in the spreadsheet for those postings.
2. Copy the job description text manually and paste it into the sheet.
3. The automation falls back to a minimal stub and still generates output.

### Row stuck at "processing"

A previous run crashed after marking the row but before completing it.
Manually set the `status` back to `not applied` in the spreadsheet to retry.

### GitHub Actions: "No module named 'services'"

Ensure `main.py` and the `services/` directory are at the repository root
(not nested in a subdirectory) and that `requirements.txt` is also at the root.

### OpenAI rate limit errors

- Reduce `MAX_JOBS_PER_RUN` to process fewer jobs per run.
- Increase `RATE_LIMIT_DELAY` (e.g. to `5`) to add more pause between jobs.
- Check your OpenAI account tier — free-tier accounts have strict rate limits.

### Checking workflow logs

In GitHub Actions:
```
Actions → Career Agent Automation → [run] → run-automation → Run career agent automation
```

Locally, check `logs/automation_YYYYMMDD.log`.
