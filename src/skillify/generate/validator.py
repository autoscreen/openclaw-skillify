from __future__ import annotations

import re

from skillify.models import SkillOutput
from skillify.util.frontmatter import parse_frontmatter


class SkillValidator:
    """Validates generated skills against OpenClaw conventions."""

    MAX_BODY_LINES = 500
    NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
    MAX_NAME_LENGTH = 64

    def validate(self, skill: SkillOutput) -> list[str]:
        """Return a list of validation errors. Empty list means valid."""
        errors = []

        # Validate name
        if not skill.name:
            errors.append("Skill name is empty")
        elif not self.NAME_PATTERN.match(skill.name):
            errors.append(
                f"Skill name '{skill.name}' must be lowercase letters, digits, and hyphens"
            )
        elif len(skill.name) > self.MAX_NAME_LENGTH:
            errors.append(
                f"Skill name '{skill.name}' exceeds {self.MAX_NAME_LENGTH} characters"
            )

        # Validate SKILL.md content
        if not skill.skill_md:
            errors.append("SKILL.md content is empty")
            return errors

        meta, body = parse_frontmatter(skill.skill_md)

        # Frontmatter checks
        if "name" not in meta:
            errors.append("Frontmatter missing 'name' field")
        if "description" not in meta:
            errors.append("Frontmatter missing 'description' field")
        elif len(meta.get("description", "")) < 20:
            errors.append("Description is too short (should be >20 characters)")

        # Body checks
        if not body.strip():
            errors.append("SKILL.md body is empty")
        else:
            line_count = len(body.splitlines())
            if line_count > self.MAX_BODY_LINES:
                errors.append(
                    f"SKILL.md body is {line_count} lines (max {self.MAX_BODY_LINES})"
                )

        return errors
