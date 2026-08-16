import json
import zipfile
from pathlib import Path

import pytest

from job_finder.backup import BackupError, create_backup, restore_backup, validate_backup
from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.jobs import JobDraft, create_job


def _create_database(tmp_path: Path):
    run_migrations(tmp_path)
    engine = create_database_engine(tmp_path)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        create_job(
            session,
            JobDraft(
                canonical_url="https://jobs.example/backup",
                company="Backup Labs",
                title="Engineer",
            ),
        )
    return engine


def test_backup_is_consistent_checksummed_and_respects_retention(tmp_path: Path) -> None:
    _create_database(tmp_path)

    first = create_backup(tmp_path, retention=2)
    second = create_backup(tmp_path, retention=2)
    third = create_backup(tmp_path, retention=2)

    manifest = validate_backup(third.path)
    backups = sorted((tmp_path / "backups").glob("job-finder-*.zip"))

    assert manifest.schema_revision is not None
    assert manifest.database_sha256
    assert first.path.exists() is False
    assert second.path.exists()
    assert len(backups) == 2


def test_restore_validates_before_replacing_and_preserves_current_database(tmp_path: Path) -> None:
    engine = _create_database(tmp_path)
    engine.dispose()
    backup = create_backup(tmp_path)
    database = tmp_path / "job-finder.db"
    database.write_bytes(b"not a database")

    restored = restore_backup(tmp_path, backup.path)

    assert restored == database
    assert database.read_bytes() != b"not a database"
    assert list(tmp_path.glob("job-finder.db.pre-restore-*"))


def test_corrupted_backup_is_rejected_without_touching_database(tmp_path: Path) -> None:
    _create_database(tmp_path)
    backup = create_backup(tmp_path)
    corrupted = tmp_path / "corrupted.zip"
    with zipfile.ZipFile(backup.path) as source, zipfile.ZipFile(corrupted, "w") as target:
        manifest = json.loads(source.read("manifest.json"))
        manifest["database_sha256"] = "0" * 64
        target.writestr("manifest.json", json.dumps(manifest))
        target.writestr("job-finder.db", source.read("job-finder.db"))

    with pytest.raises(BackupError, match="Checksum"):
        validate_backup(corrupted)
