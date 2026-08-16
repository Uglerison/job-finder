from pathlib import Path

import job_finder.database as database_module
from job_finder.database import create_database_engine, database_path, run_migrations


def test_database_engine_creates_local_database_with_wal_and_foreign_keys(tmp_path: Path) -> None:
    engine = create_database_engine(tmp_path)

    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
        foreign_keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    assert database_path(tmp_path) == tmp_path / "job-finder.db"
    assert database_path(tmp_path).is_file()
    assert journal_mode == "wal"
    assert foreign_keys == 1


def test_migrations_are_idempotent_and_record_current_revision(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    run_migrations(tmp_path)

    engine = create_database_engine(tmp_path)
    with engine.connect() as connection:
        revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()

    assert revision == "0018_scheduled_unified_searches"


def test_migration_path_requests_a_recovery_backup_before_upgrade(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_migrations(tmp_path)
    calls: list[Path] = []

    def fake_backup(data_dir: Path, *, retention: int) -> None:
        calls.append(data_dir)
        assert retention == 5

    monkeypatch.setattr(database_module, "LATEST_SCHEMA_REVISION", "older_revision")
    monkeypatch.setattr("job_finder.backup.create_backup", fake_backup)

    run_migrations(tmp_path)

    assert calls == [tmp_path]
