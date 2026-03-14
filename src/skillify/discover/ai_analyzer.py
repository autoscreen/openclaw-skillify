from __future__ import annotations

from pydantic import BaseModel, Field

from skillify.llm.client import SkillifyLLM
from skillify.llm.prompts import (
    DESCRIPTION_GENERATION_SYSTEM,
    ENDPOINT_GROUPING_SYSTEM,
    ENDPOINT_GROUPING_USER,
)
from skillify.models import APISpec, EndpointGroup


class GroupingResult(BaseModel):
    groups: list[GroupEntry]


class GroupEntry(BaseModel):
    name: str
    display_name: str
    description: str
    endpoint_indices: list[int]
    tags: list[str] = Field(default_factory=list)


class DescriptionResult(BaseModel):
    description: str


class AIAnalyzer:
    """LLM-based endpoint grouping and description enrichment."""

    def __init__(self, llm: SkillifyLLM):
        self.llm = llm

    async def group_and_enrich(self, spec: APISpec) -> APISpec:
        """Group ungrouped endpoints and enrich descriptions."""
        if not spec.endpoints:
            return spec

        # Format endpoints for the LLM
        endpoints_text = self._format_endpoints(spec)

        result = await self.llm.structured_completion(
            system=ENDPOINT_GROUPING_SYSTEM,
            user=ENDPOINT_GROUPING_USER.format(
                api_name=spec.api_name,
                base_url=spec.base_url or "N/A",
                endpoints_text=endpoints_text,
            ),
            response_model=GroupingResult,
        )

        # Convert to EndpointGroup objects
        groups = []
        for g in result.groups:
            eps = []
            for idx in g.endpoint_indices:
                if 0 <= idx < len(spec.endpoints):
                    eps.append(spec.endpoints[idx])
            if eps:
                groups.append(
                    EndpointGroup(
                        name=g.name,
                        display_name=g.display_name,
                        description=g.description,
                        endpoints=eps,
                        tags=g.tags,
                    )
                )

        spec.groups = groups
        return spec

    async def enrich_description(self, group: EndpointGroup) -> str:
        """Generate a trigger-quality description for a group."""
        endpoints_summary = "\n".join(
            f"- {ep.method} {ep.path}: {ep.summary}" for ep in group.endpoints
        )
        result = await self.llm.structured_completion(
            system=DESCRIPTION_GENERATION_SYSTEM,
            user=f"Group: {group.display_name}\nEndpoints:\n{endpoints_summary}",
            response_model=DescriptionResult,
        )
        return result.description

    def _format_endpoints(self, spec: APISpec) -> str:
        lines = []
        for i, ep in enumerate(spec.endpoints):
            params = ", ".join(
                f"{p.name}{'*' if p.required else ''}" for p in ep.parameters
            )
            lines.append(
                f"[{i}] {ep.method} {ep.path} — {ep.summary or ep.description[:80]}"
                + (f" params: ({params})" if params else "")
            )
        return "\n".join(lines)
