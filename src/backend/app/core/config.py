from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw_value!r}") from exc


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "openai_compatible"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.2
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class Settings:
    llm: LLMSettings
    runtime_dir: str = "data/runtime"
    vault_dir: str = "data/vault"


def load_settings() -> Settings:
    return Settings(
        llm=LLMSettings(
            provider=os.getenv("LLM_PROVIDER", "openai_compatible").strip()
            or "openai_compatible",
            base_url=os.getenv("LLM_BASE_URL", "").strip(),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            model=os.getenv("LLM_MODEL", "").strip(),
            temperature=_get_float_env("LLM_TEMPERATURE", 0.2),
            timeout_seconds=_get_float_env("LLM_TIMEOUT_SECONDS", 60.0),
        ),
        runtime_dir=os.getenv("RUNTIME_DIR", "data/runtime").strip()
        or "data/runtime",
        vault_dir=os.getenv("VAULT_DIR", "data/vault").strip()
        or "data/vault",
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
