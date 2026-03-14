"""Tests for the skill validator."""
from skillify.generate.validator import SkillValidator
from skillify.models import SkillOutput


def test_valid_skill():
    skill = SkillOutput(
        name="my-skill",
        path="my-skill",
        skill_md='---\nname: my-skill\ndescription: "A valid skill for testing purposes."\n---\n\n# My Skill\n\nDo things.\n',
    )
    errors = SkillValidator().validate(skill)
    assert errors == []


def test_invalid_name_uppercase():
    skill = SkillOutput(
        name="MySkill",
        path="MySkill",
        skill_md='---\nname: MySkill\ndescription: "A skill."\n---\n\n# X\n',
    )
    errors = SkillValidator().validate(skill)
    assert any("lowercase" in e for e in errors)


def test_missing_description():
    skill = SkillOutput(
        name="ok-name",
        path="ok-name",
        skill_md="---\nname: ok-name\n---\n\n# X\n",
    )
    errors = SkillValidator().validate(skill)
    assert any("description" in e.lower() for e in errors)


def test_short_description():
    skill = SkillOutput(
        name="ok-name",
        path="ok-name",
        skill_md='---\nname: ok-name\ndescription: "Short"\n---\n\n# X\n',
    )
    errors = SkillValidator().validate(skill)
    assert any("short" in e.lower() for e in errors)


def test_empty_body():
    skill = SkillOutput(
        name="ok-name",
        path="ok-name",
        skill_md='---\nname: ok-name\ndescription: "A valid description here."\n---\n',
    )
    errors = SkillValidator().validate(skill)
    assert any("body" in e.lower() for e in errors)


def test_too_long_body():
    long_body = "\n".join(f"Line {i}" for i in range(600))
    skill = SkillOutput(
        name="ok-name",
        path="ok-name",
        skill_md=f'---\nname: ok-name\ndescription: "A valid description here."\n---\n\n{long_body}\n',
    )
    errors = SkillValidator().validate(skill)
    assert any("500" in e for e in errors)
