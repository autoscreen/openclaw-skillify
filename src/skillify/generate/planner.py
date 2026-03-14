from __future__ import annotations

from dataclasses import dataclass

from skillify.models import APISpec, AuthType, EndpointGroup


@dataclass
class SkillPlan:
    """Plan for generating a single skill from an endpoint group."""

    group: EndpointGroup
    inline_endpoints: bool  # True if <=8 endpoints go in SKILL.md body
    needs_reference_file: bool  # True if >8 endpoints
    needs_auth_script: bool  # True if OAuth2 or complex auth
    skill_name: str

    INLINE_THRESHOLD = 8


class Planner:
    """Decides skill structure for each endpoint group."""

    def plan(self, spec: APISpec) -> list[SkillPlan]:
        plans = []
        for group in spec.groups:
            ep_count = len(group.endpoints)
            inline = ep_count <= SkillPlan.INLINE_THRESHOLD

            # Determine auth complexity
            auth = group.auth or spec.auth
            needs_auth_script = auth.type == AuthType.OAUTH2

            plans.append(
                SkillPlan(
                    group=group,
                    inline_endpoints=inline,
                    needs_reference_file=not inline,
                    needs_auth_script=needs_auth_script,
                    skill_name=group.name,
                )
            )

        return plans
