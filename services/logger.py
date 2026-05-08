"""
services/logger.py
==================
Structured logging setup for the career-agent-email-cover project.

Every module gets its own named logger via ``setup_logger(__name__)``.
Logs are written to both stdout (for GitHub Actions) and a dated log file
under ``logs/`` for local debugging.

Usage
-----
    from services.logger import setup_logger

    logger = setup_logger(__name__)
    logger.info("Something happened")
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_level: str = "INFO",
    logs_dir: Optional[Path] = None,
) -> logging.Logger:
    """
    Create (or retrieve) a named logger with console and optional file output.

    Parameters
    ----------
    name:
        Logger name — pass ``__name__`` from the calling module so log lines
        identify their source automatically.
    log_level:
        One of DEBUG / INFO / WARNING / ERROR / CRITICAL.
        Defaults to INFO when the string is unrecognised.
    logs_dir:
        Directory for the daily rotating log file.
        When None, only the console handler is added.

    Returns
    -------
    logging.Logger
        Configured logger.  Calling this function multiple times with the same
        ``name`` is safe — handlers are only added once.
    """
    logger = logging.getLogger(name)

    # Guard: do not add duplicate handlers if called more than once
    if logger.handlers:
        return logger

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Consistent format: timestamp | level | module | message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Console handler (captured by GitHub Actions log viewer) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- File handler (dated filename, e.g. automation_20250108.log) ---
    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"automation_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent log records from bubbling up to the root logger (avoids duplicates)
    logger.propagate = False

    return logger
