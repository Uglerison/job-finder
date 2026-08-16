"""SQLite engine, session and migration helpers for the local application."""

import sqlite3
import sys
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_SOURCE_ROOT = Path(__file__).resolve().parents[4]
_BUNDLE_ROOT_VALUE = getattr(sys, "_MEIPASS", None)
_BUNDLE_ROOT = (
    Path(_BUNDLE_ROOT_VALUE) if isinstance(_BUNDLE_ROOT_VALUE, str) and _BUNDLE_ROOT_VALUE else None
)
PROJECT_ROOT = (
    _BUNDLE_ROOT
    if _BUNDLE_ROOT is not None and (_BUNDLE_ROOT / "alembic.ini").is_file()
    else _SOURCE_ROOT
)
DATABASE_FILENAME = "job-finder.db"
LATEST_SCHEMA_REVISION = "0018_scheduled_unified_searches"


class Base(DeclarativeBase):
    """Base class for all persistent domain models."""


def database_path(data_dir: Path) -> Path:
    """Return the SQLite file location for a configured local data directory."""

    return data_dir / DATABASE_FILENAME


def database_url(data_dir: Path) -> URL:
    """Build a SQLite URL without relying on the current working directory."""

    return URL.create("sqlite+pysqlite", database=str(database_path(data_dir)))


def create_database_engine(data_dir: Path) -> Engine:
    """Create a SQLite engine with integrity and concurrent-read settings enabled."""

    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        database_url(data_dir),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(
        dbapi_connection: SQLiteConnection,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
        dbapi_connection.execute("PRAGMA journal_mode=WAL")

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions that keep database changes explicit and transactional."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def run_migrations(data_dir: Path) -> None:
    """Upgrade the configured local SQLite database to the latest schema revision."""

    data_dir.mkdir(parents=True, exist_ok=True)
    _backup_before_upgrade(data_dir)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url(data_dir).render_as_string())
    command.upgrade(config, "head")


def _backup_before_upgrade(data_dir: Path) -> None:
    """Create a recoverable snapshot only when an existing DB is behind head."""

    path = database_path(data_dir)
    if not path.is_file():
        return
    try:
        with sqlite3.connect(path) as connection:
            row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    except sqlite3.Error:
        return
    # A database without Alembic metadata is either brand new or not a
    # recoverable application database yet.  Do not make the migration path
    # fail while trying to back up such a file; Alembic will report the real
    # migration error below.
    if not row or row[0] == LATEST_SCHEMA_REVISION:
        return
    from job_finder.backup import create_backup

    create_backup(data_dir, retention=5)
