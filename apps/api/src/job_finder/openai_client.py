"""Small backend-only client for controlled OpenAI Responses API calls."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx
from pydantic import SecretStr

DEFAULT_OPENAI_MODEL: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OpenAiReasoningEffort = Literal["low", "medium"]


class OpenAiClientError(RuntimeError):
    """Base error with a safe message suitable for local API clients."""


class OpenAiAuthenticationError(OpenAiClientError):
    """Raised when OpenAI rejects the configured API key."""


class OpenAiTimeoutError(OpenAiClientError):
    """Raised when an OpenAI request exceeds the bounded local timeout."""


class OpenAiUnavailableError(OpenAiClientError):
    """Raised for temporary provider or network availability failures."""


class OpenAiResponseError(OpenAiClientError):
    """Raised when OpenAI returns an unusable response contract."""


@dataclass(frozen=True)
class OpenAiTextResponse:
    """Minimal normalized output from one Responses API call."""

    response_id: str
    model: str
    output_text: str


class OpenAiTextClient(Protocol):
    """Contract used by the local API without exposing transport details."""

    def create_text_response(self, api_key: SecretStr, input_text: str) -> OpenAiTextResponse:
        """Create one low-reasoning, non-persisted text response."""


class OpenAiStructuredClient(Protocol):
    """Contract for a strict structured response, used by job analysis only."""

    def create_structured_response(
        self,
        api_key: SecretStr,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, object],
        reasoning_effort: OpenAiReasoningEffort,
    ) -> OpenAiTextResponse:
        """Create one non-persisted response constrained by a JSON Schema."""


class OpenAiResponsesClient:
    """Use the Responses API through the backend with a per-call in-memory key."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def create_text_response(self, api_key: SecretStr, input_text: str) -> OpenAiTextResponse:
        """Call GPT-5.6 Luna without storing response state at the provider."""

        return self._create_response(
            api_key,
            {
                "input": input_text,
                "model": DEFAULT_OPENAI_MODEL,
                "reasoning": {"effort": "low"},
                "store": False,
            },
        )

    def create_structured_response(
        self,
        api_key: SecretStr,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, object],
        reasoning_effort: OpenAiReasoningEffort,
    ) -> OpenAiTextResponse:
        """Request a strictly schema-shaped analysis without provider-side storage."""

        return self._create_response(
            api_key,
            {
                "input": input_text,
                "instructions": instructions,
                "model": DEFAULT_OPENAI_MODEL,
                "reasoning": {"effort": reasoning_effort},
                "store": False,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
            },
        )

    def _create_response(
        self,
        api_key: SecretStr,
        payload: dict[str, Any],
    ) -> OpenAiTextResponse:
        """Execute one bounded Responses API request and normalize its text output."""

        try:
            with httpx.Client(
                timeout=httpx.Timeout(self._timeout_seconds),
                transport=self._transport,
            ) as client:
                response = client.post(
                    OPENAI_RESPONSES_URL,
                    headers={"Authorization": f"Bearer {api_key.get_secret_value()}"},
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise OpenAiTimeoutError("A OpenAI demorou para responder. Tente novamente.") from error
        except httpx.HTTPError as error:
            raise OpenAiUnavailableError("A OpenAI está indisponível no momento.") from error

        if response.status_code in {401, 403}:
            raise OpenAiAuthenticationError("A chave OpenAI foi recusada.")
        if response.status_code == 429 or response.status_code >= 500:
            raise OpenAiUnavailableError("A OpenAI está indisponível no momento.")
        if response.status_code >= 400:
            raise OpenAiResponseError("A OpenAI recusou a solicitação local.")

        try:
            payload = response.json()
        except ValueError as error:
            raise OpenAiResponseError("A OpenAI retornou uma resposta inválida.") from error
        if not isinstance(payload, dict):
            raise OpenAiResponseError("A OpenAI retornou uma resposta inválida.")

        output_text = _extract_output_text(payload)
        response_id = payload.get("id")
        model = payload.get("model", DEFAULT_OPENAI_MODEL)
        if not isinstance(response_id, str) or not response_id or not isinstance(model, str):
            raise OpenAiResponseError("A OpenAI retornou uma resposta incompleta.")
        return OpenAiTextResponse(
            response_id=response_id,
            model=model,
            output_text=output_text,
        )


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Read text message items from the raw Responses API payload defensively."""

    output = payload.get("output")
    if not isinstance(output, list):
        raise OpenAiResponseError("A OpenAI retornou uma resposta incompleta.")
    fragments: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                fragments.append(text)
    if not fragments:
        raise OpenAiResponseError("A OpenAI retornou uma resposta incompleta.")
    return "\n".join(fragments)
