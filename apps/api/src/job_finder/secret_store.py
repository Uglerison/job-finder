"""Encrypted local database storage for credentials that must never be logged."""

import base64
import hashlib
import os
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

    def save_openai_api_key(self, value: str, vault_password: str) -> None:
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

    def save_provider_secret(self, provider_key: str, value: str, vault_password: str) -> None:
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
        self._unlocked_key: str | None = None
        self._unlocked_provider_keys: dict[str, str] = {}

    def has_openai_api_key(self) -> bool:
        try:
            with self._session_factory() as session:
                return session.get(AiSecretRecord, 1) is not None
        except Exception as error:
            raise SecretStoreError("O cofre local está indisponível.") from error

    def save_openai_api_key(self, value: str, vault_password: str) -> None:
        try:
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
        self._unlocked_key = None
        self._unlocked_provider_keys.clear()

    def get_unlocked_openai_api_key(self) -> str | None:
        return self._unlocked_key

    def delete_openai_api_key(self) -> None:
        try:
            with self._session_factory() as session:
                record = session.get(AiSecretRecord, 1)
                if record is not None:
                    session.delete(record)
                    session.commit()
            self.lock()
        except Exception as error:
            raise SecretStoreError("Não foi possível remover a chave do cofre local.") from error

    def has_provider_secret(self, provider_key: str) -> bool:
        try:
            with self._session_factory() as session:
                return (
                    session.query(ProviderSecretRecord).filter_by(provider_key=provider_key).first()
                    is not None
                )
        except Exception as error:
            raise SecretStoreError("O cofre local está indisponível.") from error

    def save_provider_secret(self, provider_key: str, value: str, vault_password: str) -> None:
        try:
            salt = os.urandom(_SALT_LENGTH)
            ciphertext = self._encrypt(value, vault_password, salt)
            with self._session_factory() as session:
                record = (
                    session.query(ProviderSecretRecord).filter_by(provider_key=provider_key).first()
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
        try:
            with self._session_factory() as session:
                record = (
                    session.query(ProviderSecretRecord).filter_by(provider_key=provider_key).first()
                )
                if record is None:
                    raise SecretStoreError("Nenhuma credencial foi configurada para este provider.")
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
        return self._unlocked_provider_keys.get(provider_key)

    def delete_provider_secret(self, provider_key: str) -> None:
        try:
            with self._session_factory() as session:
                record = (
                    session.query(ProviderSecretRecord).filter_by(provider_key=provider_key).first()
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
