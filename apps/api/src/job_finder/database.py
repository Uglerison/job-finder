"""SQLite engine, session and migration helpers for the local application."""

from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATABASE_FILENAME = "job-finder.db"


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
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url(data_dir).render_as_string())
    command.upgrade(config, "head")
