import logging
from pathlib import Path

from job_finder.logging import configure_logging, log_file_path
from job_finder.settings import Settings


def test_local_logging_rotates_honors_levels_and_redacts_sensitive_values(
    tmp_path: Path,
) -> None:
    settings = Settings(data_dir=tmp_path, log_level="INFO", environment="test")
    logger = configure_logging(
        settings,
        logger_name="job_finder.tests.logging",
        max_bytes=180,
        backup_count=2,
    )

    logger.debug("debug message must not be recorded")
    logger.info(
        "token=sk-proj-very-secret-token email=ana.silva@example.com phone=+55 11 99876-1234"
    )
    for event_number in range(6):
        logger.info("rotation-event=%s %s", event_number, "x" * 80)

    for handler in logger.handlers:
        handler.flush()
        handler.close()

    entries = list(log_file_path(settings.data_dir).parent.glob("job-finder.log*"))
    content = "\n".join(entry.read_text(encoding="utf-8") for entry in entries)

    assert log_file_path(settings.data_dir).is_file()
    assert log_file_path(settings.data_dir).with_suffix(".log.1").is_file()
    assert "debug message" not in content
    assert "sk-proj-very-secret-token" not in content
    assert "ana.silva@example.com" not in content
    assert "+55 11 99876-1234" not in content
    assert "[REDACTED]" in content
