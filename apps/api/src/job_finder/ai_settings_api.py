"""Local-only API for encrypted OpenAI credential configuration."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, SecretStr, field_validator

from job_finder.secret_store import CredentialVault, EncryptedDatabaseVault, SecretStoreError
from job_finder.settings import Settings

DEFAULT_OPENAI_MODEL: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"

router = APIRouter(prefix="/api/ai", tags=["ai-settings"])


class AiSettingsResponse(BaseModel):
    """Safe AI configuration status that never contains credential material."""

    configured: bool
    unlocked: bool
    model: Literal["gpt-5.6-luna"] = DEFAULT_OPENAI_MODEL
    storage: Literal["encrypted_database", "environment", "not_configured"]


class ApiKeyRequest(BaseModel):
    """Key and transient local-vault password accepted only by the loopback backend."""

    api_key: SecretStr
    vault_password: SecretStr

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        key = value.get_secret_value().strip()
        if len(key) < 20 or any(character.isspace() for character in key):
            raise ValueError("Informe uma chave OpenAI válida.")
        return SecretStr(key)

    @field_validator("vault_password")
    @classmethod
    def validate_vault_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if len(password) < 12:
            raise ValueError("A senha do cofre deve ter pelo menos 12 caracteres.")
        return value


class VaultPasswordRequest(BaseModel):
    """Transient password used only to decrypt the local AI key into memory."""

    vault_password: SecretStr

    @field_validator("vault_password")
    @classmethod
    def validate_vault_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 12:
            raise ValueError("A senha do cofre deve ter pelo menos 12 caracteres.")
        return value


class OpenAiCredentialSettings:
    """Resolve a key from the encrypted database without exposing it through the API."""

    def __init__(
        self,
        vault: CredentialVault,
        environment_key: SecretStr | None,
    ) -> None:
        self._vault = vault
        self._environment_key = environment_key

    def status(self) -> AiSettingsResponse:
        if self._vault.has_openai_api_key():
            return AiSettingsResponse(
                configured=True,
                unlocked=self._vault.get_unlocked_openai_api_key() is not None,
                storage="encrypted_database",
            )
        if self._environment_value() is not None:
            return AiSettingsResponse(configured=True, unlocked=True, storage="environment")
        return AiSettingsResponse(configured=False, unlocked=False, storage="not_configured")

    def set_api_key(self, api_key: SecretStr, vault_password: SecretStr) -> AiSettingsResponse:
        self._vault.save_openai_api_key(
            api_key.get_secret_value(),
            vault_password.get_secret_value(),
        )
        return self.status()

    def unlock(self, vault_password: SecretStr) -> AiSettingsResponse:
        self._vault.unlock_openai_api_key(vault_password.get_secret_value())
        return self.status()

    def lock(self) -> AiSettingsResponse:
        self._vault.lock()
        return self.status()

    def delete_api_key(self) -> AiSettingsResponse:
        self._vault.delete_openai_api_key()
        return self.status()

    def get_api_key(self) -> SecretStr | None:
        stored_key = self._vault.get_unlocked_openai_api_key()
        if stored_key is not None:
            return SecretStr(stored_key)
        return self._environment_key

    def _environment_value(self) -> str | None:
        return self._environment_key.get_secret_value() if self._environment_key else None


def get_ai_settings(request: Request) -> OpenAiCredentialSettings:
    """Build the credential resolver from app-owned local resources."""

    vault = getattr(request.app.state, "secret_vault", None)
    if vault is None:
        session_factory = request.app.state.session_factory
        vault = EncryptedDatabaseVault(session_factory)
        request.app.state.secret_vault = vault
    settings: Settings = request.app.state.settings
    return OpenAiCredentialSettings(vault, settings.openai_api_key)


AiSettingsDependency = Annotated[OpenAiCredentialSettings, Depends(get_ai_settings)]


def translate_vault_error(error: SecretStoreError) -> HTTPException:
    """Convert expected local-vault errors to a safe HTTP response."""

    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("/settings", response_model=AiSettingsResponse)
def read_ai_settings(settings: AiSettingsDependency) -> AiSettingsResponse:
    """Report configuration state without revealing any portion of the key."""

    try:
        return settings.status()
    except SecretStoreError as error:
        raise translate_vault_error(error) from error


@router.put("/api-key", response_model=AiSettingsResponse)
def save_api_key(payload: ApiKeyRequest, settings: AiSettingsDependency) -> AiSettingsResponse:
    """Encrypt a key into SQLite and unlock it only in the running process."""

    try:
        return settings.set_api_key(payload.api_key, payload.vault_password)
    except SecretStoreError as error:
        raise translate_vault_error(error) from error


@router.post("/unlock", response_model=AiSettingsResponse)
def unlock_api_key(
    payload: VaultPasswordRequest,
    settings: AiSettingsDependency,
) -> AiSettingsResponse:
    """Unlock the encrypted key for the current local application process."""

    try:
        return settings.unlock(payload.vault_password)
    except SecretStoreError as error:
        raise translate_vault_error(error) from error


@router.post("/lock", response_model=AiSettingsResponse)
def lock_api_key(settings: AiSettingsDependency) -> AiSettingsResponse:
    """Discard the decrypted key from the running local process."""

    try:
        return settings.lock()
    except SecretStoreError as error:
        raise translate_vault_error(error) from error


@router.delete("/api-key", response_model=AiSettingsResponse)
def remove_api_key(settings: AiSettingsDependency) -> AiSettingsResponse:
    """Remove the encrypted record while leaving an environment key untouched."""

    try:
        return settings.delete_api_key()
    except SecretStoreError as error:
        raise translate_vault_error(error) from error
