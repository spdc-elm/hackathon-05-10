from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import httpx

from app.core.config import LLMSettings, get_settings


def _log_dir() -> Path:
    d = Path(os.getenv("RUNTIME_DIR", "data/runtime")) / "llm_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_exchange(label: str, request_payload: Any, response_status: int | None, response_body: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    log_file = _log_dir() / f"{ts}_{label}.json"
    entry = {
        "timestamp": ts,
        "label": label,
        "request": request_payload,
        "response_status": response_status,
        "response_body": response_body[:20000],
    }
    log_file.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")


class LLMError(Exception):
    """Base error for LLM adapter failures."""


class LLMConfigurationError(LLMError):
    """Raised when required LLM settings are missing or unsupported."""


class LLMProviderError(LLMError):
    """Raised when the configured provider returns an error response."""


class LLMResponseError(LLMError):
    """Raised when a provider response does not match the expected shape."""


class LLMJSONParseError(LLMError):
    """Raised when model output cannot be parsed as JSON."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


MessageInput = ChatMessage | Mapping[str, str]


def _message_to_dict(message: MessageInput) -> dict[str, str]:
    if isinstance(message, ChatMessage):
        return {"role": message.role, "content": message.content}

    role = message.get("role")
    content = message.get("content")
    if not role or content is None:
        raise ValueError("Each message must include 'role' and 'content'.")
    return {"role": str(role), "content": str(content)}


class LLMClient:
    async def generate_text(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        messages: Sequence[MessageInput] | None = None,
        temperature: float | None = None,
    ) -> str:
        raise NotImplementedError

    async def generate_json(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        messages: Sequence[MessageInput] | None = None,
        temperature: float | None = None,
    ) -> Any:
        text = await self.generate_text(
            prompt,
            system=system,
            messages=messages,
            temperature=temperature,
        )
        return parse_json_output(text)


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(
        self,
        settings: LLMSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._http_client = http_client

    async def generate_text(
        self,
        prompt: str | None = None,
        *,
        system: str | None = None,
        messages: Sequence[MessageInput] | None = None,
        temperature: float | None = None,
    ) -> str:
        request_messages = _build_messages(prompt, system=system, messages=messages)
        payload = {
            "model": self._require_model(),
            "messages": request_messages,
            "temperature": (
                self.settings.temperature if temperature is None else temperature
            ),
        }

        response_data = await self._post_chat_completions(payload)
        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                "LLM response did not include choices[0].message.content."
            ) from exc

        if not isinstance(content, str):
            raise LLMResponseError("LLM response content was not a string.")
        return content

    async def _post_chat_completions(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._validate_settings()
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

        # Use streaming to avoid read timeout on long generations.
        # Connection timeout stays short; read timeout is effectively infinite
        # since SSE chunks keep arriving.
        stream_payload = {**dict(payload), "stream": True}
        timeout = httpx.Timeout(
            connect=30.0,
            read=60.0,  # per-chunk read timeout, not total
            write=30.0,
            pool=30.0,
        )

        collected_content = ""
        try:
            if self._http_client is not None:
                response = await self._http_client.post(
                    url, headers=headers, json=stream_payload,
                )
                # Injected client doesn't support streaming; fall back to non-stream
                if response.status_code >= 400:
                    _log_exchange("http_error", dict(payload), response.status_code, response.text[:20000])
                    raise LLMProviderError(f"LLM provider returned HTTP {response.status_code}: {response.text}")
                data = response.json()
                _log_exchange("ok", dict(payload), response.status_code, response.text[:20000])
                if not isinstance(data, dict):
                    raise LLMResponseError("LLM provider response JSON was not an object.")
                return data
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, headers=headers, json=stream_payload) as response:
                        if response.status_code >= 400:
                            body = await response.aread()
                            body_text = body.decode(errors="replace")
                            _log_exchange("http_error", dict(payload), response.status_code, body_text[:20000])
                            raise LLMProviderError(f"LLM provider returned HTTP {response.status_code}: {body_text}")

                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content_piece = delta.get("content", "")
                                if content_piece:
                                    collected_content += content_piece
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue

        except httpx.HTTPError as exc:
            _log_exchange("error", dict(payload), None, f"{type(exc).__name__}: {exc}")
            raise LLMProviderError(f"LLM request failed: {type(exc).__name__}: {exc}") from exc

        _log_exchange("ok_stream", dict(payload), 200, collected_content[:20000])

        # Reconstruct the response in non-streaming format
        return {
            "choices": [{"message": {"role": "assistant", "content": collected_content}}]
        }

    def _require_model(self) -> str:
        if not self.settings.model:
            raise LLMConfigurationError("LLM_MODEL is required.")
        return self.settings.model

    def _validate_settings(self) -> None:
        if not self.settings.base_url:
            raise LLMConfigurationError("LLM_BASE_URL is required.")
        if not self.settings.api_key:
            raise LLMConfigurationError("LLM_API_KEY is required.")
        self._require_model()


def get_llm_client(settings: LLMSettings | None = None) -> LLMClient:
    llm_settings = settings or get_settings().llm
    if llm_settings.provider == "openai_compatible":
        return OpenAICompatibleLLMClient(llm_settings)

    raise LLMConfigurationError(
        f"Unsupported LLM_PROVIDER {llm_settings.provider!r}. "
        "Currently supported: openai_compatible."
    )


async def generate_text(
    prompt: str | None = None,
    *,
    system: str | None = None,
    messages: Sequence[MessageInput] | None = None,
    temperature: float | None = None,
    client: LLMClient | None = None,
) -> str:
    llm_client = client or get_llm_client()
    return await llm_client.generate_text(
        prompt,
        system=system,
        messages=messages,
        temperature=temperature,
    )


async def generate_json(
    prompt: str | None = None,
    *,
    system: str | None = None,
    messages: Sequence[MessageInput] | None = None,
    temperature: float | None = None,
    client: LLMClient | None = None,
) -> Any:
    llm_client = client or get_llm_client()
    return await llm_client.generate_json(
        prompt,
        system=system,
        messages=messages,
        temperature=temperature,
    )


def parse_json_output(text: str) -> Any:
    candidates = _json_candidates(text)
    last_error: json.JSONDecodeError | None = None

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc

    message = "LLM output was not valid JSON."
    if last_error is not None:
        message = f"{message} {last_error.msg} at line {last_error.lineno}, column {last_error.colno}."
    raise LLMJSONParseError(message)


def _build_messages(
    prompt: str | None,
    *,
    system: str | None,
    messages: Sequence[MessageInput] | None,
) -> list[dict[str, str]]:
    if prompt is None and not messages:
        raise ValueError("Either prompt or messages must be provided.")

    built_messages: list[dict[str, str]] = []
    if system:
        built_messages.append({"role": "system", "content": system})
    if messages:
        built_messages.extend(_message_to_dict(message) for message in messages)
    if prompt is not None:
        built_messages.append({"role": "user", "content": prompt})
    return built_messages


def _json_candidates(text: str) -> list[str]:
    stripped = text.strip()
    candidates = [stripped] if stripped else []

    fenced_blocks = re.findall(
        r"```(?:json|JSON)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL,
    )
    candidates.extend(block.strip() for block in fenced_blocks if block.strip())

    # Prefer direct JSON first, but also handle common prose wrappers around an object.
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(stripped[first_brace : last_brace + 1])

    first_bracket = stripped.find("[")
    last_bracket = stripped.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        candidates.append(stripped[first_bracket : last_bracket + 1])

    return list(dict.fromkeys(candidates))
