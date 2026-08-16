from pathlib import Path

import pytest

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.secret_store import EncryptedDatabaseVault, SecretStoreError


def create_vault(data_dir: Path) -> EncryptedDatabaseVault:
    """Create a migrated vault backed by one isolated SQLite database."""

    run_migrations(data_dir)
    engine = create_database_engine(data_dir)
    return EncryptedDatabaseVault(create_session_factory(engine))


def test_database_vault_encrypts_unlocks_locks_and_removes_an_api_key(tmp_path: Path) -> None:
    vault = create_vault(tmp_path)
    secret = "sk-test-only-12345678901234567890"
    vault_password = "uma senha local longa"

    assert vault.has_openai_api_key() is False
    assert vault.get_unlocked_openai_api_key() is None

    vault.save_openai_api_key(secret, vault_password)

    assert vault.has_openai_api_key() is True
    assert vault.get_unlocked_openai_api_key() == secret

    vault.lock()
    assert vault.get_unlocked_openai_api_key() is None

    vault.unlock_openai_api_key(vault_password)
    assert vault.get_unlocked_openai_api_key() == secret

    vault.delete_openai_api_key()
    assert vault.has_openai_api_key() is False
    assert vault.get_unlocked_openai_api_key() is None


def test_database_vault_never_persists_plaintext_or_password(tmp_path: Path) -> None:
    secret = "sk-test-never-in-sqlite-1234567890"
    vault_password = "uma senha local muito longa"
    vault = create_vault(tmp_path)

    vault.save_openai_api_key(secret, vault_password)

    database_bytes = (tmp_path / "job-finder.db").read_bytes()
    assert secret.encode() not in database_bytes
    assert vault_password.encode() not in database_bytes


def test_database_vault_rejects_a_wrong_password_without_leaking_secrets(tmp_path: Path) -> None:
    secret = "sk-test-never-leak-1234567890123"
    vault = create_vault(tmp_path)
    vault.save_openai_api_key(secret, "senha certa e longa")
    vault.lock()

    with pytest.raises(SecretStoreError, match="desbloquear") as error:
        vault.unlock_openai_api_key("senha errada e longa")

    assert secret not in str(error.value)


def test_database_vault_supports_provider_credentials_without_plaintext(tmp_path: Path) -> None:
    vault = create_vault(tmp_path)
    secret = "jsearch-test-key"
    password = "senha do cofre com doze"

    assert vault.has_provider_secret("jsearch") is False
    vault.save_provider_secret("jsearch", secret, password)
    assert vault.has_provider_secret("jsearch") is True
    assert vault.get_unlocked_provider_secret("jsearch") == secret

    vault.lock()
    assert vault.get_unlocked_provider_secret("jsearch") is None
    vault.unlock_provider_secret("jsearch", password)
    assert vault.get_unlocked_provider_secret("jsearch") == secret

    database_bytes = (tmp_path / "job-finder.db").read_bytes()
    assert secret.encode() not in database_bytes
    vault.delete_provider_secret("jsearch")
    assert vault.has_provider_secret("jsearch") is False
