from __future__ import annotations

import shutil
from pathlib import Path

from skillify.generate.planner import Planner
from skillify.generate.reference_writer import ReferenceWriter
from skillify.generate.script_writer import ScriptWriter
from skillify.generate.skill_writer import SkillWriter
from skillify.generate.validator import SkillValidator
from skillify.llm.client import SkillifyLLM
from skillify.models import APISpec, GenerationResult


async def generate(
    spec: APISpec,
    output_dir: str | Path = "./skills",
    model: str | None = None,
    dry_run: bool = False,
    install: bool = False,
) -> GenerationResult:
    """Generate OpenClaw skills from an APISpec.

    Args:
        spec: The discovered API specification.
        output_dir: Where to write generated skill directories.
        model: LLM model for generation steps.
        dry_run: If True, return result without writing to disk.
        install: If True, also copy to ~/.nanobot/workspace/skills/.
    """
    llm = SkillifyLLM(model=model)
    planner = Planner()
    writer = SkillWriter(llm)
    ref_writer = ReferenceWriter()
    script_writer = ScriptWriter()
    validator = SkillValidator()

    plans = planner.plan(spec)
    skills = []

    for plan in plans:
        skill = await writer.write(plan, spec)

        if plan.needs_reference_file:
            refs = ref_writer.write(plan, spec)
            skill.references.update(refs)

        if plan.needs_auth_script:
            scripts = script_writer.write(plan, spec)
            skill.scripts.update(scripts)

        errors = validator.validate(skill)
        if errors:
            import sys
            for err in errors:
                print(f"  Warning [{skill.name}]: {err}", file=sys.stderr)

        skills.append(skill)

    result = GenerationResult(api_name=spec.api_name, skills=skills, spec=spec)

    if not dry_run:
        out = Path(output_dir)
        _write_to_disk(result, out)

        if install:
            nanobot_skills = Path.home() / ".nanobot" / "workspace" / "skills"
            nanobot_skills.mkdir(parents=True, exist_ok=True)
            for skill in result.skills:
                src = out / skill.name
                dst = nanobot_skills / skill.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

    return result


def _write_to_disk(result: GenerationResult, output_dir: Path) -> None:
    """Write generated skills to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for skill in result.skills:
        skill_dir = output_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        (skill_dir / "SKILL.md").write_text(skill.skill_md)

        # Write references
        if skill.references:
            ref_dir = skill_dir / "references"
            ref_dir.mkdir(exist_ok=True)
            for filename, content in skill.references.items():
                (ref_dir / filename).write_text(content)

        # Write scripts
        if skill.scripts:
            script_dir = skill_dir / "scripts"
            script_dir.mkdir(exist_ok=True)
            for filename, content in skill.scripts.items():
                path = script_dir / filename
                path.write_text(content)
                path.chmod(0o755)
