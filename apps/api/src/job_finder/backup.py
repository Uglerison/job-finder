"""Consistent, checksummed local database backups and safe restoration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from job_finder.database import DATABASE_FILENAME, database_path

BACKUP_FORMAT_VERSION = 1
BACKUP_DIRECTORY_NAME = "backups"
MANIFEST_FILENAME = "manifest.json"
SNAPSHOT_FILENAME = DATABASE_FILENAME


class BackupError(RuntimeError):
    """Raised when a backup cannot be created, validated or restored safely."""


@dataclass(frozen=True)
class BackupManifest:
    format_version: int
    created_at: str
    schema_revision: str | None
    database_filename: str
    database_sha256: str
    database_size: int


@dataclass(frozen=True)
class BackupResult:
    path: Path
    manifest: BackupManifest


def create_backup(
    data_dir: Path,
    *,
    destination_dir: Path | None = None,
    retention: int = 5,
) -> BackupResult:
    """Snapshot SQLite consistently and atomically publish a zipped backup."""

    source = database_path(data_dir)
    if not source.is_file():
        raise BackupError("O banco local ainda não existe.")
    if retention < 1:
        raise BackupError("A retenção deve manter ao menos um backup.")

    target_dir = destination_dir or data_dir / BACKUP_DIRECTORY_NAME
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="job-finder-backup-", dir=target_dir) as temp_name:
        temporary_dir = Path(temp_name)
        snapshot = temporary_dir / SNAPSHOT_FILENAME
        _snapshot_sqlite(source, snapshot)
        manifest = _build_manifest(snapshot)
        (temporary_dir / MANIFEST_FILENAME).write_text(
            json.dumps(manifest.__dict__, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        final_path = target_dir / f"job-finder-{stamp}-{manifest.database_sha256[:12]}.zip"
        temporary_zip = target_dir / f".{final_path.name}.tmp"
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(temporary_dir / MANIFEST_FILENAME, MANIFEST_FILENAME)
            archive.write(snapshot, SNAPSHOT_FILENAME)
        _fsync_file(temporary_zip)
        os.replace(temporary_zip, final_path)

    _prune_backups(target_dir, retention)
    return BackupResult(path=final_path, manifest=manifest)


def validate_backup(backup_path: Path) -> BackupManifest:
    """Validate archive structure, manifest, checksum and SQLite integrity."""

    if not backup_path.is_file():
        raise BackupError("Arquivo de backup não encontrado.")
    try:
        with zipfile.ZipFile(backup_path) as archive:
            names = set(archive.namelist())
            if names != {MANIFEST_FILENAME, SNAPSHOT_FILENAME}:
                raise BackupError("Backup contém arquivos inesperados.")
            manifest_data = json.loads(archive.read(MANIFEST_FILENAME))
            manifest = BackupManifest(**manifest_data)
            if manifest.format_version != BACKUP_FORMAT_VERSION:
                raise BackupError("Formato de backup incompatível.")
            if manifest.database_filename != SNAPSHOT_FILENAME:
                raise BackupError("Manifesto aponta para um banco inesperado.")
            with tempfile.TemporaryDirectory(prefix="job-finder-validate-") as temp_name:
                snapshot = Path(temp_name) / SNAPSHOT_FILENAME
                with archive.open(SNAPSHOT_FILENAME) as source, snapshot.open("wb") as target:
                    shutil.copyfileobj(source, target)
                if snapshot.stat().st_size != manifest.database_size:
                    raise BackupError("Tamanho do banco não confere com o manifesto.")
                if _sha256(snapshot) != manifest.database_sha256:
                    raise BackupError("Checksum do banco não confere com o manifesto.")
                _check_sqlite(snapshot)
            return manifest
    except (KeyError, TypeError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        if isinstance(error, BackupError):
            raise
        raise BackupError("Backup inválido ou corrompido.") from error


def restore_backup(data_dir: Path, backup_path: Path) -> Path:
    """Validate a backup, preserve the current DB, then atomically replace it."""

    manifest = validate_backup(backup_path)
    current = database_path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="job-finder-restore-", dir=data_dir) as temp_name:
        temporary_db = Path(temp_name) / SNAPSHOT_FILENAME
        with zipfile.ZipFile(backup_path) as archive, archive.open(SNAPSHOT_FILENAME) as source:
            with temporary_db.open("wb") as target:
                shutil.copyfileobj(source, target)
        _check_sqlite(temporary_db)
        preserved = data_dir / (
            f"{DATABASE_FILENAME}.pre-restore-"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
        if current.exists():
            shutil.copy2(current, preserved)
            _fsync_file(preserved)
        try:
            os.replace(temporary_db, current)
        except PermissionError:
            # Windows does not replace an existing file in every situation
            # (for example when a pooled SQLite handle is still attached).
            # The current database has already been preserved above, so a
            # controlled unlink lets the atomic move complete without losing
            # the rollback copy.
            try:
                current.unlink()
                os.replace(temporary_db, current)
            except OSError as replace_error:
                raise BackupError(
                    "Não foi possível substituir o banco atual. "
                    "Feche o Job Finder e tente novamente."
                ) from replace_error
    if _sha256(current) != manifest.database_sha256:
        raise BackupError("O banco restaurado não passou na validação final.")
    return current


def _snapshot_sqlite(source: Path, destination: Path) -> None:
    try:
        with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as target:
            source_connection.backup(target)
            target.commit()
    except sqlite3.Error as error:
        raise BackupError("Não foi possível criar um snapshot consistente do banco.") from error
    _fsync_file(destination)


def _build_manifest(snapshot: Path) -> BackupManifest:
    revision: str | None = None
    try:
        with sqlite3.connect(snapshot) as connection:
            row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
            revision = str(row[0]) if row else None
    except sqlite3.Error as error:
        raise BackupError("Banco local inválido para backup.") from error
    return BackupManifest(
        format_version=BACKUP_FORMAT_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        schema_revision=revision,
        database_filename=SNAPSHOT_FILENAME,
        database_sha256=_sha256(snapshot),
        database_size=snapshot.stat().st_size,
    )


def _check_sqlite(path: Path) -> None:
    try:
        with sqlite3.connect(path) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if result != ("ok",):
                raise BackupError("O banco do backup falhou na verificação de integridade.")
    except sqlite3.Error as error:
        raise BackupError("O arquivo do backup não é um banco SQLite válido.") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    # Windows rejects fsync on a read-only handle.  Opening for read/write
    # keeps the operation portable while still avoiding any content change.
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def _prune_backups(directory: Path, retention: int) -> None:
    backups = sorted(directory.glob("job-finder-*.zip"), key=lambda item: item.stat().st_mtime)
    for old_backup in backups[:-retention]:
        old_backup.unlink(missing_ok=True)
