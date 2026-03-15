from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

import litellm
from litellm import acompletion

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"

# API key env vars that litellm recognises, mapped to the key name
# we store in keys.json.
_KEY_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
]


def _resolve_model(model: str | None = None) -> str:
    """Resolve model from arg, env vars, or default."""
    if model:
        return model
    return os.environ.get(
        "SKILLIFY_MODEL",
        os.environ.get("LITELLM_MODEL", DEFAULT_MODEL),
    )


def _load_api_keys_from_store() -> None:
    """Populate environment with API keys from keys.json.

    Only sets a variable if it isn't already present in the environment,
    so explicit env vars always take precedence.
    """
    from skillify.keys import _load

    stored = _load()
    for env_var in _KEY_ENV_VARS:
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
