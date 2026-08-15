"""Local logging configured for diagnostics without retaining sensitive values."""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from job_finder.settings import Settings

LOG_DIRECTORY_NAME = "logs"
LOG_FILENAME = "job-finder.log"
DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_BACKUP_COUNT = 3

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b"), "[REDACTED]"),
    (
        re.compile(
            r"\b(?:authorization|api[_-]?key|token|password|secret)\s*[:=]\s*"
            r"(?:Bearer\s+)?[^\s,;]+",
            flags=re.IGNORECASE,
        ),
        "[REDACTED]",
    ),
    (
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE),
        "[REDACTED]",
    ),
    (re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)"), "[REDACTED]"),
)


class RedactingFormatter(logging.Formatter):
    """Format a record only after replacing known secret and contact-data patterns."""

    def format(self, record: logging.LogRecord) -> str:
        rendered_record = super().format(record)
        for pattern, replacement in _REDACTIONS:
            rendered_record = pattern.sub(replacement, rendered_record)
        return rendered_record


def log_file_path(data_dir: Path) -> Path:
    """Return the versioned location of the local rotating application log."""

    return data_dir / LOG_DIRECTORY_NAME / LOG_FILENAME


def configure_logging(
    settings: Settings,
    *,
    logger_name: str = "job_finder",
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Configure one independent rotating local logger from runtime settings."""

    path = log_file_path(settings.data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(settings.log_level)
    logger.propagate = False
    for existing_handler in logger.handlers[:]:
        logger.removeHandler(existing_handler)
        existing_handler.close()

    handler = RotatingFileHandler(
        path,
        encoding="utf-8",
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    return logger


def close_logging(logger: logging.Logger) -> None:
    """Flush and close this logger's file handles, which is required on Windows."""

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
