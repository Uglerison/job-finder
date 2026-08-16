from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from job_finder.main import create_app
from job_finder.openai_client import OpenAiTextResponse, OpenAiUnavailableError
from job_finder.secret_store import SecretStoreError
from job_finder.settings import Settings


class FakeEncryptedVault:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.unlocked_value: str | None = None
        self.error: Exception | None = None

    def has_openai_api_key(self) -> bool:
        if self.error:
            raise self.error
        return self.value is not None

    def save_openai_api_key(self, value: str, vault_password: str) -> None:
        if self.error:
            raise self.error
        self.value = value
        self.unlocked_value = value

    def unlock_openai_api_key(self, vault_password: str) -> None:
        if self.error:
            raise self.error
        if self.value is None:
            raise SecretStoreError("Nenhuma chave foi configurada.")
        self.unlocked_value = self.value

    def lock(self) -> None:
        self.unlocked_value = None

    def get_unlocked_openai_api_key(self) -> str | None:
        return self.unlocked_value

    def delete_openai_api_key(self) -> None:
        if self.error:
            raise self.error
        self.value = None
        self.unlocked_value = None


class FakeOpenAiClient:
    def __init__(self) -> None:
        self.error: Exception | None = None
        self.received_key: SecretStr | None = None
        self.received_input: str | None = None

    def create_text_response(self, api_key: SecretStr, input_text: str) -> OpenAiTextResponse:
        if self.error:
            raise self.error
        self.received_key = api_key
        self.received_input = input_text
        return OpenAiTextResponse(
            response_id="resp_test_123",
            model="gpt-5.6-luna",
            output_text="conexão local confirmada",
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def application(tmp_path: Path):
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.secret_vault = FakeEncryptedVault()
    app.state.openai_client = FakeOpenAiClient()
    return app


@pytest.mark.anyio
async def test_ai_settings_api_saves_locks_unlocks_and_removes_an_encrypted_key(
    application,
) -> None:
    transport = ASGITransport(app=application)
    secret = "sk-test-only-12345678901234567890"
    vault_password = "uma senha local longa"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        initial = await client.get("/api/ai/settings")
        saved = await client.put(
            "/api/ai/api-key",
            json={"api_key": secret, "vault_password": vault_password},
        )
        locked = await client.post("/api/ai/lock")
        unlock = await client.post(
            "/api/ai/unlock",
            json={"vault_password": vault_password},
        )
        removed = await client.delete("/api/ai/api-key")

    assert initial.json() == {
        "configured": False,
        "unlocked": False,
        "model": "gpt-5.6-luna",
        "storage": "not_configured",
    }
    assert saved.status_code == 200
    assert saved.json() == {
        "configured": True,
        "unlocked": True,
        "model": "gpt-5.6-luna",
        "storage": "encrypted_database",
    }
    assert locked.json()["unlocked"] is False
    assert unlock.json()["unlocked"] is True
    assert removed.json() == {
        "configured": False,
        "unlocked": False,
        "model": "gpt-5.6-luna",
        "storage": "not_configured",
    }
    for response in (saved, locked, unlock, removed):
        assert secret not in response.text
        assert vault_password not in response.text


@pytest.mark.anyio
async def test_ai_settings_api_can_report_an_environment_key_without_exposing_it(
    tmp_path: Path,
) -> None:
    secret = "sk-environment-12345678901234567890"
    app = create_app(
        Settings(data_dir=tmp_path, environment="test", openai_api_key=secret),
    )
    app.state.secret_vault = FakeEncryptedVault()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/ai/settings")

    assert response.json() == {
        "configured": True,
        "unlocked": True,
        "model": "gpt-5.6-luna",
        "storage": "environment",
    }
    assert secret not in response.text


@pytest.mark.anyio
async def test_ai_settings_api_returns_safe_error_when_encrypted_storage_is_unavailable(
    application,
) -> None:
    vault = application.state.secret_vault
    vault.error = SecretStoreError("O cofre local está indisponível.")
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/ai/api-key",
            json={
                "api_key": "sk-test-only-12345678901234567890",
                "vault_password": "uma senha local longa",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "O cofre local está indisponível."}


@pytest.mark.anyio
async def test_ai_connection_test_uses_the_unlocked_key_only_in_the_backend(application) -> None:
    secret = "sk-test-only-12345678901234567890"
    vault = application.state.secret_vault
    vault.value = secret
    vault.unlocked_value = secret
    openai_client = application.state.openai_client
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/ai/connection/test")

    assert response.json() == {"status": "connected", "model": "gpt-5.6-luna"}
    assert openai_client.received_key is not None
    assert openai_client.received_key.get_secret_value() == secret
    assert openai_client.received_input == "Responda apenas: conexão local confirmada."
    assert secret not in response.text


@pytest.mark.anyio
async def test_ai_connection_test_requires_an_unlocked_key_and_maps_provider_failure(
    application,
) -> None:
    transport = ASGITransport(app=application)
    openai_client = application.state.openai_client

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        locked = await client.post("/api/ai/connection/test")

    assert locked.status_code == 409
    assert locked.json() == {
        "detail": "Configure e desbloqueie a chave OpenAI para testar a conexão."
    }

    vault = application.state.secret_vault
    vault.value = "sk-test-only-12345678901234567890"
    vault.unlocked_value = vault.value
    openai_client.error = OpenAiUnavailableError("A OpenAI está indisponível no momento.")

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        unavailable = await client.post("/api/ai/connection/test")

    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "A OpenAI está indisponível no momento."}
