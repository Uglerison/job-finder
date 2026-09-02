"""Encrypted local database storage for credentials that must never be logged."""

import base64
import hashlib
import os
from threading import RLock
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from job_finder.database import Base

_KDF_LENGTH = 32
_KDF_N = 2**14
_KDF_R = 8
_KDF_P = 1
_SALT_LENGTH = 16
_VAULT_MARKER = "_vault_session"


class SecretStoreError(RuntimeError):
    """Raised with a safe message when the local encrypted vault cannot be used."""


class AiSecretRecord(Base):
    """Singleton encrypted credential record; neither plaintext nor password is persisted."""

    __tablename__ = "ai_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    salt: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class ProviderSecretRecord(Base):
    """Encrypted credentials for external job providers."""

    __tablename__ = "provider_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    salt: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class CredentialVault(Protocol):
    """Application-facing contract for the encrypted OpenAI API credential."""

    def has_openai_api_key(self) -> bool:
        """Report whether an encrypted key is persisted."""

    def save_openai_api_key(self, value: str, vault_password: str | None) -> None:
        """Encrypt and persist a key, then make it available only in process memory."""

    def unlock_openai_api_key(self, vault_password: str) -> None:
        """Decrypt the stored key into process memory using the supplied password."""

    def lock(self) -> None:
        """Discard the decrypted key from process memory."""

    def get_unlocked_openai_api_key(self) -> str | None:
        """Return the in-memory key only while the vault is unlocked."""

    def delete_openai_api_key(self) -> None:
        """Remove the encrypted record and its in-memory value."""

    def has_provider_secret(self, provider_key: str) -> bool:
        """Report whether a provider credential is encrypted in SQLite."""

    def save_provider_secret(
        self, provider_key: str, value: str, vault_password: str | None
    ) -> None:
        """Encrypt and persist a provider credential."""

    def unlock_provider_secret(self, provider_key: str, vault_password: str) -> None:
        """Decrypt one provider credential into process memory."""

    def get_unlocked_provider_secret(self, provider_key: str) -> str | None:
        """Return a provider credential only while it is unlocked."""

    def delete_provider_secret(self, provider_key: str) -> None:
        """Remove one encrypted provider credential."""


class EncryptedDatabaseVault:
    """SQLite-backed OpenAI key vault unlocked by an unpersisted local password."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._mutex = RLock()
        self._unlocked_key: str | None = None
        self._unlocked_provider_keys: dict[str, str] = {}
        self._session_password: str | None = None

    def is_configured(self) -> bool:
        with self._mutex:
            with self._session_factory() as session:
                return session.get(AiSecretRecord, 1) is not None or (
                    session.query(ProviderSecretRecord).first() is not None
                )

    def is_unlocked(self) -> bool:
        with self._mutex:
            return self._session_password is not None

    def initialize(self, password: str) -> None:
        with self._mutex:
            if self.is_configured():
                raise SecretStoreError("O cofre já existe. Use a senha atual para desbloquear.")
            self.save_provider_secret(_VAULT_MARKER, "job-finder-vault-v1", password)
            self._session_password = password

    def unlock_all(self, password: str) -> None:
        """Publish decrypted values only after every stored credential validates."""
        with self._mutex:
            try:
                with self._session_factory() as session:
                    ai = session.get(AiSecretRecord, 1)
                    providers = session.query(ProviderSecretRecord).all()
                    if ai is None and not providers:
                        raise SecretStoreError("Crie o cofre local antes de desbloquear.")
                    ai_key = self._decrypt(ai.ciphertext, password, ai.salt) if ai else None
                    provider_keys = {
                        row.provider_key: self._decrypt(row.ciphertext, password, row.salt)
                        for row in providers
                    }
                if _VAULT_MARKER not in provider_keys:
                    self.save_provider_secret(_VAULT_MARKER, "job-finder-vault-v1", password)
                provider_keys.pop(_VAULT_MARKER, None)
                self._unlocked_key = ai_key
                self._unlocked_provider_keys = provider_keys
                self._session_password = password
            except Exception:
                self.lock()
                raise SecretStoreError(
                    "Não foi possível desbloquear todas as credenciais. "
                    "Verifique a senha do cofre. "
                    "Credenciais antigas com senhas diferentes precisam ser revisadas."
                ) from None

    def _password_for_save(self, password: str | None) -> str:
        resolved = password if password is not None else self._session_password
        if resolved is None:
            raise SecretStoreError("Desbloqueie o cofre local antes de salvar a credencial.")
        with self._session_factory() as session:
            marker = (
                session.query(ProviderSecretRecord).filter_by(provider_key=_VAULT_MARKER).first()
            )
            if marker is not None:
                self._decrypt(marker.ciphertext, resolved, marker.salt)
        return resolved

    def has_openai_api_key(self) -> bool:
        with self._mutex:
            try:
                with self._session_factory() as session:
                    return session.get(AiSecretRecord, 1) is not None
            except Exception as error:
                raise SecretStoreError("O cofre local está indisponível.") from error

    def save_openai_api_key(self, value: str, vault_password: str | None) -> None:
        with self._mutex:
            try:
                vault_password = self._password_for_save(vault_password)
                salt = os.urandom(_SALT_LENGTH)
                ciphertext = self._encrypt(value, vault_password, salt)
                with self._session_factory() as session:
                    record = session.get(AiSecretRecord, 1)
                    if record is None:
                        record = AiSecretRecord(id=1, ciphertext=ciphertext, salt=salt)
                        session.add(record)
                    else:
                        record.ciphertext = ciphertext
                        record.salt = salt
                    session.commit()
                self._unlocked_key = value
            except SecretStoreError:
                raise
            except Exception as error:
                raise SecretStoreError("Não foi possível salvar a chave no cofre local.") from error

    def unlock_openai_api_key(self, vault_password: str) -> None:
        with self._mutex:
            try:
                with self._session_factory() as session:
                    record = session.get(AiSecretRecord, 1)
                    if record is None:
                        raise SecretStoreError("Nenhuma chave foi configurada.")
                    self._unlocked_key = self._decrypt(
                        bytes(record.ciphertext),
                        vault_password,
                        bytes(record.salt),
                    )
            except SecretStoreError:
                raise
            except Exception as error:
                raise SecretStoreError("O cofre local está indisponível.") from error

    def lock(self) -> None:
        with self._mutex:
            self._unlocked_key = None
            self._unlocked_provider_keys.clear()
            self._session_password = None

    def get_unlocked_openai_api_key(self) -> str | None:
        with self._mutex:
            return self._unlocked_key

    def delete_openai_api_key(self) -> None:
        with self._mutex:
            try:
                with self._session_factory() as session:
                    record = session.get(AiSecretRecord, 1)
                    if record is not None:
                        session.delete(record)
                        session.commit()
                self.lock()
            except Exception as error:
                raise SecretStoreError(
                    "Não foi possível remover a chave do cofre local."
                ) from error

    def has_provider_secret(self, provider_key: str) -> bool:
        with self._mutex:
            try:
                with self._session_factory() as session:
                    return (
                        session.query(ProviderSecretRecord)
                        .filter_by(provider_key=provider_key)
                        .first()
                        is not None
                    )
            except Exception as error:
                raise SecretStoreError("O cofre local está indisponível.") from error

    def save_provider_secret(
        self, provider_key: str, value: str, vault_password: str | None
    ) -> None:
        with self._mutex:
            try:
                vault_password = self._password_for_save(vault_password)
                salt = os.urandom(_SALT_LENGTH)
                ciphertext = self._encrypt(value, vault_password, salt)
                with self._session_factory() as session:
                    record = (
                        session.query(ProviderSecretRecord)
                        .filter_by(provider_key=provider_key)
                        .first()
                    )
                    if record is None:
                        session.add(
                            ProviderSecretRecord(
                                provider_key=provider_key,
                                ciphertext=ciphertext,
                                salt=salt,
                            ),
                        )
                    else:
                        record.ciphertext = ciphertext
                        record.salt = salt
                    session.commit()
                self._unlocked_provider_keys[provider_key] = value
            except Exception as error:
                raise SecretStoreError(
                    "Não foi possível salvar a credencial no cofre local."
                ) from error

    def unlock_provider_secret(self, provider_key: str, vault_password: str) -> None:
        with self._mutex:
            try:
                with self._session_factory() as session:
                    record = (
                        session.query(ProviderSecretRecord)
                        .filter_by(provider_key=provider_key)
                        .first()
                    )
                    if record is None:
                        raise SecretStoreError(
                            "Nenhuma credencial foi configurada para este provider."
                        )
                    self._unlocked_provider_keys[provider_key] = self._decrypt(
                        bytes(record.ciphertext),
                        vault_password,
                        bytes(record.salt),
                    )
            except SecretStoreError:
                raise
            except Exception as error:
                raise SecretStoreError("O cofre local está indisponível.") from error

    def get_unlocked_provider_secret(self, provider_key: str) -> str | None:
        with self._mutex:
            return self._unlocked_provider_keys.get(provider_key)

    def delete_provider_secret(self, provider_key: str) -> None:
        with self._mutex:
            try:
                with self._session_factory() as session:
                    record = (
                        session.query(ProviderSecretRecord)
                        .filter_by(provider_key=provider_key)
                        .first()
                    )
                    if record is not None:
                        session.delete(record)
                        session.commit()
                self._unlocked_provider_keys.pop(provider_key, None)
            except Exception as error:
                raise SecretStoreError(
                    "Não foi possível remover a credencial do cofre local."
                ) from error

    @staticmethod
    def _encrypt(value: str, vault_password: str, salt: bytes) -> bytes:
        return EncryptedDatabaseVault._fernet(vault_password, salt).encrypt(value.encode("utf-8"))

    @staticmethod
    def _decrypt(ciphertext: bytes, vault_password: str, salt: bytes) -> str:
        try:
            return (
                EncryptedDatabaseVault._fernet(vault_password, salt)
                .decrypt(ciphertext)
                .decode("utf-8")
            )
        except (InvalidToken, UnicodeDecodeError) as error:
            raise SecretStoreError(
                "Não foi possível desbloquear a chave. Verifique a senha do cofre."
            ) from error

    @staticmethod
    def _fernet(vault_password: str, salt: bytes) -> Fernet:
        derived_key = hashlib.scrypt(
            vault_password.encode("utf-8"),
            salt=salt,
            n=_KDF_N,
            r=_KDF_R,
            p=_KDF_P,
            dklen=_KDF_LENGTH,
        )
        return Fernet(base64.urlsafe_b64encode(derived_key))
