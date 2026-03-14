from __future__ import annotations

import json

from skillify.generate.planner import SkillPlan
from skillify.llm.client import SkillifyLLM
from skillify.llm.prompts import EMOJI_SYSTEM, SKILL_BODY_SYSTEM
from skillify.models import APISpec, AuthType, SkillOutput
from skillify.util.frontmatter import render_frontmatter

from pydantic import BaseModel


class EmojiResult(BaseModel):
    emoji: str


class SkillWriter:
    """Generates SKILL.md content for a skill plan."""

    def __init__(self, llm: SkillifyLLM):
        self.llm = llm

    async def write(self, plan: SkillPlan, spec: APISpec) -> SkillOutput:
        group = plan.group
        auth = group.auth or spec.auth

        # Get emoji from LLM
        emoji = await self._get_emoji(group.display_name, spec.api_name)

        # Build metadata
        nanobot_meta: dict = {"emoji": emoji}
        requires: dict = {}
        if auth.env_var:
            requires["env"] = [auth.env_var]
        if requires:
            nanobot_meta["requires"] = requires
        metadata_json = {"nanobot": nanobot_meta}

        # Build frontmatter
        frontmatter = {
            "name": plan.skill_name,
            "description": group.description,
            "metadata": metadata_json,
        }

        # Generate body
        body = await self._generate_body(plan, spec)

        skill_md = render_frontmatter(frontmatter, body)

        return SkillOutput(
            name=plan.skill_name,
            path=plan.skill_name,
            skill_md=skill_md,
            metadata=metadata_json,
        )

    async def _generate_body(self, plan: SkillPlan, spec: APISpec) -> str:
        """Generate the markdown body, using LLM for polishing."""
        group = plan.group
        auth = group.auth or spec.auth

        # Build a context string for the LLM
        endpoints_desc = []
        for ep in group.endpoints:
            params_str = ""
            if ep.parameters:
                params_str = "\n    Parameters: " + ", ".join(
                    f"{p.name} ({p.type}, {'required' if p.required else 'optional'})"
                    for p in ep.parameters
                )
            endpoints_desc.append(
                f"  {ep.method} {ep.path} — {ep.summary or ep.description[:80]}{params_str}"
            )

        user_prompt = (
            f"API: {spec.api_name}\n"
            f"Group: {group.display_name}\n"
            f"Base URL: {spec.base_url or 'N/A'}\n"
            f"Auth: {self._describe_auth(auth)}\n"
            f"Inline all endpoints: {plan.inline_endpoints}\n"
            f"Has reference file: {plan.needs_reference_file}\n"
            f"\nEndpoints:\n" + "\n".join(endpoints_desc)
        )

        body = await self.llm.completion(
            system=SKILL_BODY_SYSTEM,
            user=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        # If it has reference file, append a link
        if plan.needs_reference_file:
            body = body.rstrip()
            body += "\n\n## Full Endpoint Reference\n\n"
            body += "See [references/endpoints.md](references/endpoints.md) for all endpoints.\n"

        return body

    async def _get_emoji(self, display_name: str, api_name: str) -> str:
        try:
            result = await self.llm.structured_completion(
                system=EMOJI_SYSTEM,
                user=f"API: {api_name}, Resource: {display_name}",
                response_model=EmojiResult,
            )
            return result.emoji
        except Exception:
            return "🔌"

    def _describe_auth(self, auth) -> str:
        if auth.type == AuthType.NONE:
            return "None"
        if auth.type == AuthType.BEARER_TOKEN:
            return f"Bearer token in {auth.header_name or 'Authorization'} header, env var: ${auth.env_var or 'API_TOKEN'}"
        if auth.type == AuthType.API_KEY_HEADER:
            return f"API key in {auth.header_name or 'X-API-Key'} header, env var: ${auth.env_var or 'API_KEY'}"
        if auth.type == AuthType.API_KEY_QUERY:
            return f"API key as query parameter, env var: ${auth.env_var or 'API_KEY'}"
        if auth.type == AuthType.BASIC_AUTH:
            return "Basic authentication"
        if auth.type == AuthType.OAUTH2:
            return f"OAuth2, env var: ${auth.env_var or 'OAUTH_TOKEN'}"
        return str(auth.type)
