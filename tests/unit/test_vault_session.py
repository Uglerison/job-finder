from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.secret_store import EncryptedDatabaseVault, SecretStoreError


def make_vault(tmp_path: Path) -> EncryptedDatabaseVault:
    run_migrations(tmp_path)
    return EncryptedDatabaseVault(create_session_factory(create_database_engine(tmp_path)))


def test_initialized_vault_rejects_a_different_password_on_individual_saves(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    vault.initialize("senha unica e longa")
    with pytest.raises(SecretStoreError):
        vault.save_provider_secret("jooble", "key", "outra senha diferente")
    with pytest.raises(SecretStoreError):
        vault.save_openai_api_key("sk-test-only", "outra senha diferente")
    assert not vault.has_provider_secret("jooble")
    assert not vault.has_openai_api_key()


def test_lock_waits_for_an_in_flight_unlock_and_leaves_session_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = make_vault(tmp_path)
    vault.initialize("senha unica e longa")
    vault.save_openai_api_key("sk-test-only", None)
    vault.lock()
    decrypting, release, locking, locked = Event(), Event(), Event(), Event()
    decrypt = vault._decrypt

    def slow_decrypt(ciphertext: bytes, password: str, salt: bytes) -> str:
        decrypting.set()
        assert release.wait(3)
        return decrypt(ciphertext, password, salt)

    def lock() -> None:
        locking.set()
        vault.lock()
        locked.set()

    monkeypatch.setattr(vault, "_decrypt", slow_decrypt)
    with ThreadPoolExecutor(max_workers=2) as executor:
        unlock_task = executor.submit(vault.unlock_all, "senha unica e longa")
        assert decrypting.wait(3)
        lock_task = executor.submit(lock)
        try:
            assert locking.wait(3)
            assert not locked.wait(0.1)
        finally:
            release.set()
            unlock_task.result(timeout=3)
            lock_task.result(timeout=3)
    assert not vault.is_unlocked()
    assert vault.get_unlocked_openai_api_key() is None
