"""
services package
================
Modular service layer for the career-agent-email-cover project.

Modules
-------
config             — centralized configuration (env vars + defaults)
logger             — structured logging factory
sheets             — Google Sheets read/write operations
drive              — Google Drive folder management and file upload
openai_client      — OpenAI chat-completion with retry logic
scraper            — job-page web scraping (requests + BeautifulSoup)
prompts            — all AI prompt templates (system + user)
document_generator — Markdown and DOCX file creation
resume_optimizer   — PDF text extraction and optimized profile loading
"""
