from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

import litellm
from litellm import acompletion

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "openrouter/anthropic/claude-sonnet-4-5"


def _resolve_model(model: str | None = None) -> str:
    """Resolve model from arg, env vars, or default."""
    if model:
        return model
    return os.environ.get(
        "SKILLIFY_MODEL",
        os.environ.get("LITELLM_MODEL", DEFAULT_MODEL),
    )


class SkillifyLLM:
    """Thin wrapper around litellm for skillify's AI-aided steps."""

    def __init__(self, model: str | None = None):
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
