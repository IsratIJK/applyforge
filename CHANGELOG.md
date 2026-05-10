# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.6.1] — 2026-05-11

### Fixed

- **Full Guide page stuck on "Loading README…"** — two bugs in `docs/readme.html`:
  1. Heading renderer destructured `{ text, depth }` but in marked v9 the token
     carries `{ tokens, depth }` — `text` is always `undefined`, causing
     `text.replace(...)` to throw inside `marked.parse()`. Fixed by using
     `{ tokens, depth }` and rendering via `this.parser.parseInline(tokens)`.
  2. All post-fetch DOM manipulation was outside the `try/catch`, so any exception
     produced a silent failure with no error shown. Entire `loadReadme` body is
     now inside a single `try/catch`.
- Heading slug generation strips HTML tags from the rendered text before slugifying,
  so headings with inline markup (`**bold**`, `` `code` ``) produce clean anchor IDs.

---

## [1.6.0] — 2026-05-11

### Added

- **Full Guide page** (`docs/readme.html`) — renders the repository README inside
  the docs site with syntax-highlighted code blocks, copy buttons on every snippet,
  and working table-of-contents anchor links.
- Copy buttons on all Command Deck snippets in the docs homepage.
- `docs-site.yml` CI step to copy `README.md` into `docs/` before artifact upload,
  making the file accessible to the Full Guide page on GitHub Pages.
- `docs/README.md` added to `.gitignore` so the CI-generated copy is never committed.

### Changed

- Docs site nav link renamed from "README" to "Full Guide" and now points to
  `readme.html` instead of the raw `../README.md` file (which is unreachable on
  GitHub Pages).
- Command code blocks in the docs site now render with `white-space: pre` so
  multi-line commands display correctly.

---

## [1.5.0] — 2026-05-10

### Changed

- **Breaking: Resume profiles moved from repository files to GitHub Variables.**
  Profiles were previously committed to `resumes/` (safe only in a private repo).
  Now that the repository is public, profiles are stored as GitHub Actions
  Repository Variables (`RESUME_DEFAULT`, `RESUME_BACKEND`, `RESUME_AI`, etc.)
  and injected at runtime via environment variables — no resume content ever
  touches the repository.
- `services/resume_optimizer.py` — `load_resume_profile()` now resolves profiles
  in priority order: env var `RESUME_{TYPE}` → local file `resumes/{type}.txt` →
  env var `RESUME_DEFAULT` → local file `resumes/default.txt`. Local file fallback
  preserves existing local-dev workflows.
- `.gitignore` — added `resumes/*.txt`; profiles are no longer tracked.
- `resumes/default.txt` removed from version control.
- `automation.yml` — passes `RESUME_DEFAULT`, `RESUME_BACKEND`, and `RESUME_AI`
  from Repository Variables as environment variables to the Python runtime.
- `example.env` — documents the new `RESUME_*` variable section.

### Migration from v1.4.x

1. Run `python scripts/process_resume.py` to generate `.txt` profiles locally.
2. Copy each profile's content into a GitHub Actions Repository Variable:
   **Settings → Secrets and variables → Actions → Variables → New repository variable**
   - `RESUME_DEFAULT` — content of `resumes/default.txt`
   - `RESUME_BACKEND` — content of `resumes/backend.txt` (if you use this type)
   - `RESUME_AI` — content of `resumes/ai.txt` (if you use this type)
3. Local `.txt` files remain usable for local dev but are now gitignored.

---

## [1.4.1] — 2026-05-10

### Added

- Added the new ApplyForge overview graphic under `docs/assets/` and embedded
  it in both the docs homepage and the repository README.

### Changed

- Centralized the project hero image in a shared docs asset path so GitHub
  Pages and GitHub README rendering stay in sync.

---

## [1.4.0] — 2026-05-10

### Changed

- Rebranded project from `career-agent-email-cover` / "Career Agent" to
  `applyforge` / "ApplyForge" across README, docs site, workflows, config
  references, and runtime-facing labels.
- Updated clone examples, GitHub Actions workflow names, Google Cloud naming
  examples, and release metadata to use the new project name consistently.

---

## [1.3.0] — 2026-05-10

### Added

- Static documentation website under `docs/` with tutorial cards, workflow
  overview, configuration highlights, project layout, status values, and command
  reference.
- GitHub Pages deployment workflow at `.github/workflows/docs-site.yml` for
  publishing the `docs/` directory from GitHub Actions.

### Changed

- README now links and documents the new docs website, local preview command,
  GitHub Pages activation steps, and updated project structure.

---

## [1.2.1] — 2026-05-10

### Added

- Unit test suite under `tests/` covering config validation, document generation,
  and resume optimizer behavior.

### Changed

- README now documents unit test execution and includes `tests/` in project
  structure.

---

## [1.2.0] — 2026-05-09

### Fixed

- **Google Drive `403 storageQuotaExceeded`** — service accounts have zero
  personal Drive storage quota and cannot upload to regular "My Drive" folders.
  Switched Drive auth to OAuth2 user credentials so files are uploaded as the
  real Google account owner.

### Added

- `scripts/generate_refresh_token.py` — one-time local script that opens a
  browser for Google login and prints the three credential values to save as
  GitHub Secrets.
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`,
  `GOOGLE_OAUTH_REFRESH_TOKEN` config fields in `services/config.py`.
- `GOOGLE_DRIVE_FOLDER_ID` config field — set to the Drive folder ID from the
  folder URL for reliable targeting without name-based search.
- `supportsAllDrives=True` and `includeItemsFromAllDrives=True` on all Drive
  API calls for forward compatibility with Shared Drives.
- `google-auth-oauthlib>=1.2.0` dependency.

### Changed

- `services/drive.py` now prefers OAuth2 user credentials over service-account
  credentials when `GOOGLE_OAUTH_REFRESH_TOKEN` is present. Service-account
  auth remains as a fallback for Shared Drive setups.
- GitHub Actions workflow exposes three new OAuth2 secrets.
- `oauth_client.json` added to `.gitignore`.

---

## [1.1.0] — 2026-05-09

### Fixed

- **Blank directories missing after `git clone`** — `.gitignore` patterns used
  `dir/` which prevents negation rules from working inside the directory. Changed
  to `dir/*` so `.gitkeep` files are correctly unignored.
- **GitHub Actions Node.js 20 deprecation warning** — added
  `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` at workflow level to opt into
  Node.js 24 ahead of the September 2026 forced migration.

### Added

- `.gitkeep` files in `raw_resumes/`, `output/`, and `logs/` so all expected
  directories exist immediately after cloning.

### Changed

- Removed `resumes/*.txt` from `.gitignore` — profiles are committed directly
  since this is a private repository, eliminating the need for GitHub Secrets
  to hold resume content at runtime.

---

## [1.0.0] — 2026-05-08

### Added

- Initial release.
- Daily automation via GitHub Actions (`0 19 * * *` UTC = 1:00 AM BST).
- Google Sheets integration: reads `not applied` rows, writes status updates
  throughout processing.
- Job-page scraping with `requests` + `BeautifulSoup` — no headless browser.
- OpenAI cover letter and recruiter email generation with exponential backoff
  and separate rate-limit handling.
- Google Drive upload organized into `Applications/<Company>/` sub-folders.
- Two-phase resume pipeline: preprocess PDFs once with
  `scripts/process_resume.py`, use compact `.txt` profiles at runtime
  (~55% token reduction per job).
- Output formats: `.md` (plain text) and `.docx` (formatted Word document).
- All credentials stored as GitHub Secrets — no JSON files on disk.
- Manual workflow trigger with `max_jobs` and `log_level` overrides.
- Artifact upload of generated documents (30-day retention in Actions UI).
- Per-job failure isolation — one failure does not stop the rest of the run.

[1.6.1]: https://github.com/FahimFBA/applyforge/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/FahimFBA/applyforge/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/FahimFBA/applyforge/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/FahimFBA/applyforge/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/FahimFBA/applyforge/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/FahimFBA/applyforge/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/FahimFBA/applyforge/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/FahimFBA/applyforge/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/FahimFBA/applyforge/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/FahimFBA/applyforge/releases/tag/v1.0.0
