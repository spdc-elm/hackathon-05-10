import json

import httpx
import pytest

from app.core.config import LLMSettings
from app.services.llm import (
    LLMJSONParseError,
    LLMProviderError,
    OpenAICompatibleLLMClient,
    generate_json,
    parse_json_output,
)


@pytest.mark.asyncio
async def test_openai_compatible_request_construction() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "adapter response"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                base_url="https://llm.example.test/v1/",
                api_key="test-key",
                model="test-model",
                temperature=0.4,
                timeout_seconds=3,
            ),
            http_client=http_client,
        )

        result = await client.generate_text("Say hi", system="Be concise")

    assert result == "adapter response"
    assert captured["url"] == "https://llm.example.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["payload"] == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": "Say hi"},
        ],
        "temperature": 0.4,
        "stream": True,
    }


def test_parse_json_output_from_plain_json() -> None:
    assert parse_json_output('{"ok": true, "items": [1, 2]}') == {
        "ok": True,
        "items": [1, 2],
    }


def test_parse_json_output_from_fenced_json() -> None:
    assert parse_json_output('Here:\n```json\n{"answer": 42}\n```') == {
        "answer": 42
    }


def test_parse_json_output_raises_clear_error() -> None:
    with pytest.raises(LLMJSONParseError, match="not valid JSON"):
        parse_json_output("```json\nnot-json\n```")


@pytest.mark.asyncio
async def test_generate_json_uses_client_and_parses_fenced_json() -> None:
    class FakeClient:
        async def generate_json(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return parse_json_output('```json\n{"merged": true}\n```')

    assert await generate_json("Return JSON", client=FakeClient()) == {
        "merged": True
    }


@pytest.mark.asyncio
async def test_provider_http_error_is_wrapped() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                base_url="https://llm.example.test/v1",
                api_key="test-key",
                model="test-model",
            ),
            http_client=http_client,
        )

        with pytest.raises(LLMProviderError, match="HTTP 429"):
            await client.generate_text("hello")
