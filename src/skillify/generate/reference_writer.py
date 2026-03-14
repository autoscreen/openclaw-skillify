from __future__ import annotations

from skillify.generate.planner import SkillPlan
from skillify.models import APISpec


class ReferenceWriter:
    """Generates reference files for large endpoint groups."""

    def write(self, plan: SkillPlan, spec: APISpec) -> dict[str, str]:
        """Returns a dict of filename -> content for references/."""
        group = plan.group
        auth = group.auth or spec.auth

        lines = [
            f"# {group.display_name} — Full Endpoint Reference",
            "",
            f"Base URL: `{spec.base_url or 'N/A'}`",
            "",
            "## Table of Contents",
            "",
        ]

        # TOC
        for ep in group.endpoints:
            anchor = _make_anchor(ep.method, ep.path)
            lines.append(f"- [{ep.method} {ep.path}](#{anchor}) — {ep.summary}")

        lines.append("")

        # Endpoint details
        for ep in group.endpoints:
            lines.append(f"## {ep.method} {ep.path}")
            lines.append("")
            if ep.summary:
                lines.append(ep.summary)
                lines.append("")
            if ep.description and ep.description != ep.summary:
                lines.append(ep.description)
                lines.append("")

            if ep.parameters:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Name | In | Type | Required | Description |")
                lines.append("|------|----|------|----------|-------------|")
                for p in ep.parameters:
                    req = "Yes" if p.required else "No"
                    lines.append(
                        f"| `{p.name}` | {p.location} | {p.type} | {req} | {p.description} |"
                    )
                lines.append("")

            if ep.request_body_schema:
                lines.append("**Request body:**")
                lines.append("")
                lines.append("```json")
                import json
                lines.append(json.dumps(ep.request_body_schema, indent=2)[:500])
                lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

        return {"endpoints.md": "\n".join(lines)}


def _make_anchor(method: str, path: str) -> str:
    """Generate a markdown anchor from method + path."""
    text = f"{method.lower()}-{path}"
    import re
    text = re.sub(r"[^a-z0-9-]", "-", text.lower())
    text = re.sub(r"-+", "-", text).strip("-")
    return text
