"""
services/resume_optimizer.py
=============================
Resume text extraction and optimized profile loading.

This module has two distinct responsibilities:

1. **Extraction** (used by scripts/process_resume.py at preprocessing time)
   ``extract_pdf_text(pdf_path)`` — pull raw text from a PDF using PyMuPDF.

2. **Loading** (used by main.py at job-processing time)
   ``load_resume_profile(resumes_dir, resume_type)`` — return the pre-optimized
   .txt profile for a given resume type key (e.g. "backend", "ai", "default").

Why two-phase?
--------------
Sending a raw PDF to OpenAI on every job application wastes tokens and money.
The PDF is processed once via the script, and the compact optimized profile is
reused for every subsequent application that matches that resume type.

Token savings vs raw PDF
------------------------
* A typical 2-page PDF: ~1 500 tokens (raw text)
* Optimized profile: ~350–450 tokens
* Saving per application: ~75 % reduction in resume-context tokens

Usage
-----
    from services.resume_optimizer import extract_pdf_text, load_resume_profile
    from pathlib import Path

    raw_text = extract_pdf_text(Path("raw_resumes/backend.pdf"))
    profile  = load_resume_profile(Path("resumes"), resume_type="backend")
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF — zero-dependency PDF reader; no external binary required

from services.logger import setup_logger

logger = setup_logger(__name__)


# ======================================================================== #
# PDF extraction                                                             #
# ======================================================================== #

def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extract all text from a PDF file using PyMuPDF.

    PyMuPDF (fitz) is chosen over pdfminer / pdfplumber because it handles
    a wide range of PDF encodings and is significantly faster.

    Parameters
    ----------
    pdf_path:
        Path to the source PDF file.

    Returns
    -------
    str
        Cleaned, normalised plain text from all pages.

    Raises
    ------
    FileNotFoundError
        If the PDF does not exist at the given path.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages: list[str] = []
    with fitz.open(str(pdf_path)) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                pages.append(page_text)
            else:
                logger.debug(f"Page {page_num} of '{pdf_path.name}' appears to be image-only — skipped")

    raw_text = "\n".join(pages)
    return _clean_extracted_text(raw_text)


def _clean_extracted_text(text: str) -> str:
    """
    Normalise common PDF extraction artefacts.

    Operations (in order)
    ---------------------
    1. Replace common PDF bullet/arrow code-points with a plain hyphen.
    2. Strip non-ASCII characters that are typically encoding artefacts.
    3. Collapse runs of more than two consecutive newlines.
    4. Collapse multiple spaces to a single space.
    """
    # Common PDF symbol code-points that appear as garbage characters
    text = re.sub(r"[•●]", "-", text)

    # Non-ASCII artefacts (ligatures, smart quotes rendered as ? chars, etc.)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Collapse excessive blank lines (3+ → 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


# ======================================================================== #
# Profile loading                                                            #
# ======================================================================== #

def load_resume_profile(resumes_dir: Path, resume_type: str) -> str:
    """
    Load a pre-optimized resume profile by type key.

    Resolution order
    ----------------
    1. ``resumes_dir / {resume_type}.txt``
    2. ``resumes_dir / default.txt``   (fallback when type-specific file missing)

    Parameters
    ----------
    resumes_dir:
        Directory containing optimized .txt profiles (from config.resumes_dir).
    resume_type:
        Key from the spreadsheet ``resume_type`` column (e.g. "backend", "ai").

    Returns
    -------
    str
        Content of the matching optimized profile.

    Raises
    ------
    FileNotFoundError
        If neither the requested type nor default.txt exists.
    ValueError
        If the located profile file is empty.
    """
    profile_path = resumes_dir / f"{resume_type}.txt"

    if not profile_path.exists():
        logger.warning(
            f"Resume profile '{resume_type}.txt' not found in {resumes_dir}/ — "
            f"falling back to default.txt"
        )
        profile_path = resumes_dir / "default.txt"

    if not profile_path.exists():
        raise FileNotFoundError(
            f"No resume profile found for type '{resume_type}' and no default.txt present. "
            f"Run:  python scripts/process_resume.py"
        )

    content = profile_path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError(
            f"Resume profile is empty: {profile_path}. "
            f"Re-run scripts/process_resume.py to regenerate it."
        )

    logger.info(f"Loaded resume profile: '{profile_path.name}' ({len(content)} chars)")
    return content
