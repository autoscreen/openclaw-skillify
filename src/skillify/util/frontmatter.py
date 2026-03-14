from __future__ import annotations

import json
import re

import yaml


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown. Returns (metadata, body)."""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return {}, content
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, match.group(2).strip()


def render_frontmatter(metadata: dict, body: str) -> str:
    """Render YAML frontmatter + markdown body into a SKILL.md string.

    Follows nanobot convention: metadata field is a single-line JSON string.
    """
    lines = ["---"]
    for key, value in metadata.items():
        if key == "metadata" and isinstance(value, dict):
            lines.append(f"metadata: {json.dumps(value, ensure_ascii=False)}")
        elif isinstance(value, str) and _needs_quoting(value):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    if not body.endswith("\n"):
        lines.append("")
    return "\n".join(lines)


def _needs_quoting(s: str) -> bool:
    """Check if a YAML string value needs quoting."""
    if not s:
        return True
    # Quote if contains special chars or starts with special YAML chars
    special_starts = {"{", "[", "*", "&", "!", "%", "@", "`", "'", '"', "|", ">"}
    if s[0] in special_starts:
        return True
    if any(c in s for c in (":", "#", ",")):
        return True
    return False
