from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

import litellm
from litellm import acompletion

T = TypeVar("T", bound=BaseModel)

_FALLBACK_MODEL = "anthropic/claude-sonnet-4-5"

# API key env vars that litellm recognises, in priority order for
# auto-detecting which provider to use.
_PROVIDER_KEYS = [
    ("ANTHROPIC_API_KEY", "anthropic/claude-sonnet-4-5"),
    ("OPENROUTER_API_KEY", "openrouter/anthropic/claude-sonnet-4-5"),
    ("OPENAI_API_KEY", "openai/gpt-4o"),
    ("GEMINI_API_KEY", "gemini/gemini-2.0-flash"),
    ("DEEPSEEK_API_KEY", "deepseek/deepseek-chat"),
    ("GROQ_API_KEY", "groq/llama-3.3-70b-versatile"),
]


def _resolve_model(model: str | None = None) -> str:
    """Resolve model from arg → env → keys.json → auto-detect from available key."""
    if model:
        return model

    # Check env var
    from_env = os.environ.get("SKILLIFY_MODEL") or os.environ.get("LITELLM_MODEL")
    if from_env:
        return from_env

    # Check keys.json for SKILLIFY_MODEL
    from skillify.keys import get_key

    stored_model = get_key("SKILLIFY_MODEL")
    if stored_model:
        return stored_model

    # Auto-detect from whichever provider key is available
    for env_var, default_model in _PROVIDER_KEYS:
        if os.environ.get(env_var):
            return default_model

    return _FALLBACK_MODEL


def _load_api_keys_from_store() -> None:
    """Populate environment with API keys from keys.json.

    Only sets a variable if it isn't already present in the environment,
    so explicit env vars always take precedence.
    """
    from skillify.keys import _load

    stored = _load()
    for env_var, _ in _PROVIDER_KEYS:
        if env_var not in os.environ and env_var in stored:
            os.environ[env_var] = stored[env_var]


class SkillifyLLM:
    """Thin wrapper around litellm for skillify's AI-aided steps."""

    def __init__(self, model: str | None = None):
        _load_api_keys_from_store()
        self.model = _resolve_model(model)
        litellm.suppress_debug_info = True
        litellm.drop_params = True

    async def structured_completion(
        self,
        system: str,
        user: str,
        response_model: type[T],
        temperature: float = 0.2,
    ) -> T:
        """Get a structured JSON response parsed into a Pydantic model."""
        response = await acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return response_model.model_validate_json(raw)

    async def completion(self, system: str, user: str, **kwargs) -> str:
        """Simple text completion."""
        response = await acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **kwargs,
        )
        return response.choices[0].message.content
