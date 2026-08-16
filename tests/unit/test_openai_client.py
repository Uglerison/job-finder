import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from job_finder.openai_client import (
    DEFAULT_OPENAI_MODEL,
    OpenAiAuthenticationError,
    OpenAiResponsesClient,
    OpenAiTimeoutError,
    OpenAiUnavailableError,
)


def test_responses_client_uses_luna_low_reasoning_and_disabled_response_storage() -> None:
    secret = "sk-test-only-12345678901234567890"
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["headers"] = dict(request.headers)
        received["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "resp_test_123",
                "model": DEFAULT_OPENAI_MODEL,
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "conexão local confirmada"}],
                    }
                ],
            },
        )

    client = OpenAiResponsesClient(transport=httpx.MockTransport(handler))
    result = client.create_text_response(SecretStr(secret), "Teste de conexão local.")

    assert result.response_id == "resp_test_123"
    assert result.model == DEFAULT_OPENAI_MODEL
    assert result.output_text == "conexão local confirmada"
    assert received["headers"]["authorization"] == f"Bearer {secret}"
    assert received["payload"] == {
        "input": "Teste de conexão local.",
        "model": DEFAULT_OPENAI_MODEL,
        "reasoning": {"effort": "low"},
        "store": False,
    }


def test_responses_client_maps_auth_timeout_and_service_errors_without_leaking_key() -> None:
    secret = "sk-live-should-not-leak-1234567890"

    def auth_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    with pytest.raises(OpenAiAuthenticationError) as auth_error:
        OpenAiResponsesClient(transport=httpx.MockTransport(auth_handler)).create_text_response(
            SecretStr(secret),
            "Teste",
        )

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("network timeout", request=request)

    with pytest.raises(OpenAiTimeoutError) as timeout_error:
        OpenAiResponsesClient(transport=httpx.MockTransport(timeout_handler)).create_text_response(
            SecretStr(secret),
            "Teste",
        )

    def unavailable_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})

    with pytest.raises(OpenAiUnavailableError) as unavailable_error:
        OpenAiResponsesClient(
            transport=httpx.MockTransport(unavailable_handler)
        ).create_text_response(
            SecretStr(secret),
            "Teste",
        )

    for error in (auth_error.value, timeout_error.value, unavailable_error.value):
        assert secret not in str(error)


def test_responses_client_sends_a_strict_json_schema_without_storing_the_response() -> None:
    secret = "sk-test-only-12345678901234567890"
    received: dict[str, Any] = {}
    schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
        "additionalProperties": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        received["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "resp_structured_123",
                "model": DEFAULT_OPENAI_MODEL,
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"title":"Data Analyst"}'}],
                    }
                ],
            },
        )

    client = OpenAiResponsesClient(transport=httpx.MockTransport(handler))
    result = client.create_structured_response(
        SecretStr(secret),
        instructions="Extraia uma vaga.",
        input_text="Vaga não confiável: Data Analyst.",
        schema_name="job_analysis",
        schema=schema,
        reasoning_effort="medium",
    )

    assert result.response_id == "resp_structured_123"
    assert received["payload"] == {
        "input": "Vaga não confiável: Data Analyst.",
        "instructions": "Extraia uma vaga.",
        "model": DEFAULT_OPENAI_MODEL,
        "reasoning": {"effort": "medium"},
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "job_analysis",
                "strict": True,
                "schema": schema,
            }
        },
    }


def test_responses_client_normalizes_usage_and_latency_without_requiring_usage() -> None:
    clock_values = iter((10.0, 10.042))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "resp_usage_123",
                "model": DEFAULT_OPENAI_MODEL,
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "input_tokens_details": {"cached_tokens": 25},
                    "output_tokens": 40,
                    "output_tokens_details": {"reasoning_tokens": 10},
                },
            },
        )

    result = OpenAiResponsesClient(
        transport=httpx.MockTransport(handler),
        clock=lambda: next(clock_values),
    ).create_text_response(SecretStr("sk-test-only-12345678901234567890"), "Teste")

    assert result.latency_ms == 42
    assert result.usage.input_tokens == 100
    assert result.usage.cached_input_tokens == 25
    assert result.usage.output_tokens == 40
    assert result.usage.reasoning_tokens == 10
