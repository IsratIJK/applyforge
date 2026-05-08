"""
services/prompts.py
===================
All AI prompt templates for the career-agent-email-cover project.

Design principles
-----------------
* Every prompt is a module-level constant so it can be updated without
  touching any business logic.
* Templates use Python's ``str.format()`` placeholders (``{variable}``).
* Prompts are tuned to produce human-sounding, ATS-friendly output —
  not generic AI boilerplate.
* Token efficiency: prompts are concise and instruct the model to be concise.

Prompt inventory
----------------
RESUME_OPTIMIZER_SYSTEM / _USER
    Used by scripts/process_resume.py to compress a raw PDF into a compact
    structured profile.  Run once per resume; output stored in resumes/*.txt.

COVER_LETTER_SYSTEM / _USER
    Used at job-processing time to generate the ATS-optimized cover letter.

RECRUITER_EMAIL_SYSTEM / _USER
    Used at job-processing time to generate the short recruiter outreach email.
"""
from __future__ import annotations

# ======================================================================== #
# Resume optimizer prompts                                                   #
# Used by: scripts/process_resume.py                                         #
# ======================================================================== #

RESUME_OPTIMIZER_SYSTEM: str = """You are an expert technical resume optimizer and ATS specialist.
Your task: convert a raw resume into a compact, structured profile optimized for AI prompting.
Rules:
- Be concise. No filler words. No redundancy.
- Preserve all technical keywords, tools, frameworks, and metrics.
- Remove personal addresses, references, and irrelevant hobbies.
- Output must be plain text — no markdown headers, no bullet symbols beyond hyphens.
- Total output must be under 450 words."""

RESUME_OPTIMIZER_USER: str = """Extract and compress this resume into a structured profile.

Use exactly these section labels (omit any section with no relevant content):

PROFESSIONAL SUMMARY:
[2-3 sentences — role-focused, metric-driven where possible]

KEY TECHNICAL SKILLS:
[comma-separated list — languages, frameworks, tools, cloud platforms]

EXPERIENCE HIGHLIGHTS:
[3-5 lines — format: Role | Company | Key achievement or responsibility]

NOTABLE PROJECTS:
[3-5 lines — format: Project name | Tech stack | Outcome or scale]

DOMAIN EXPERTISE:
[comma-separated domains, e.g. backend engineering, distributed systems, NLP]

EDUCATION:
[Degree | Institution | Year]

CERTIFICATIONS:
[list if present, else omit this section entirely]

Constraints:
- Each highlight/project line must be under 20 words
- No filler: omit "responsible for", "worked on", "helped with"
- Preserve all numeric metrics (e.g. "reduced latency by 40%")
- Final output under 450 words

Resume text:
{resume_text}"""


# ======================================================================== #
# Cover letter prompts                                                        #
# Used by: main.py → process_job()                                           #
# ======================================================================== #

COVER_LETTER_SYSTEM: str = """You are an expert career coach and technical writer.
You write personalized, ATS-optimized cover letters that sound authentically human.

Rules:
- Match technical keywords from the job description naturally — never force them.
- Show genuine interest in the specific company, not generic enthusiasm.
- Highlight 2-3 achievements that directly map to the role's requirements.
- Avoid these openers: "I am writing to apply", "I am excited to", "I would like to".
- No hollow phrases: "team player", "go-getter", "passionate about", "results-driven".
- Professional but warm tone — a senior engineer talking to another professional.
- Under 350 words. Plain text, no markdown."""

COVER_LETTER_USER: str = """Write a professional ATS-optimized cover letter for this application.

CANDIDATE RESUME PROFILE:
{resume_profile}

APPLICATION DETAILS:
Company: {company}
Role: {role}

JOB DESCRIPTION:
{job_description}

Structure:
1. Opening paragraph — specific hook about the company/role (1–2 sentences)
2. Body paragraph — 2-3 most relevant achievements mapped to the JD requirements
3. Body paragraph — technical depth: specific skills from the JD you bring
4. Closing paragraph — clear call-to-action, enthusiasm without clichés

Output: plain text only, under 350 words."""


# ======================================================================== #
# Recruiter email prompts                                                     #
# Used by: main.py → process_job()                                           #
# ======================================================================== #

RECRUITER_EMAIL_SYSTEM: str = """You are an expert at writing concise, high-response-rate recruiter outreach emails.

Rules:
- Recruiters skim — get to the value proposition in the first sentence.
- Be confident, not pushy. Direct, not robotic.
- Mention 1-2 specific skills that match the job — no generic claims.
- Under 200 words for the body (excluding subject line).
- Plain text output."""

RECRUITER_EMAIL_USER: str = """Write a concise recruiter email for this job application.

CANDIDATE RESUME PROFILE:
{resume_profile}

APPLICATION DETAILS:
Company: {company}
Role: {role}

JOB DESCRIPTION:
{job_description}

Format (output exactly in this order):
Subject: [compelling subject line under 10 words]

[Opening — 1 sentence: who you are + strongest matching credential]

[2-3 sentences: specific skills/experience that match this role's requirements]

[1 sentence: why this company specifically — not generic]

[Closing — 1 sentence CTA + placeholder for contact info: "[Your Phone] | [Your Email]"]

Constraints:
- Body under 200 words
- No bullet points — flowing sentences only
- No hollow phrases: "passionate", "team player", "results-driven"
- Plain text, no markdown"""
