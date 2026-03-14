"""Tests for core data models."""
import json

from skillify.models import (
    APISpec,
    AuthSpec,
    AuthType,
    Endpoint,
    EndpointGroup,
    GenerationResult,
    Parameter,
    SkillOutput,
)


def test_apispec_roundtrip():
    """APISpec serializes to JSON and back."""
    spec = APISpec(
        source="https://example.com/api.json",
        source_type="openapi",
        api_name="Test API",
        api_description="A test",
        base_url="https://example.com",
        version="1.0",
        auth=AuthSpec(
            type=AuthType.BEARER_TOKEN,
            env_var="TEST_TOKEN",
            header_name="Authorization",
            header_prefix="Bearer",
        ),
        endpoints=[
            Endpoint(
                method="GET",
                path="/items",
                summary="List items",
                parameters=[
                    Parameter(name="limit", location="query", type="integer"),
                ],
                tags=["items"],
            )
        ],
        groups=[
            EndpointGroup(
                name="test-items",
                display_name="Test Items",
                description="Manage items.",
                endpoints=[
                    Endpoint(method="GET", path="/items", summary="List items")
                ],
            )
        ],
        raw_endpoint_count=1,
    )

    json_str = spec.model_dump_json()
    restored = APISpec.model_validate_json(json_str)

    assert restored.api_name == "Test API"
    assert restored.auth.type == AuthType.BEARER_TOKEN
    assert len(restored.endpoints) == 1
    assert len(restored.groups) == 1
    assert restored.groups[0].name == "test-items"


def test_apispec_empty():
    """APISpec works with minimal fields."""
    spec = APISpec(source="test", source_type="openapi", api_name="Empty")
    assert spec.endpoints == []
    assert spec.groups == []
    assert spec.auth.type == AuthType.NONE


def test_skill_output_roundtrip():
    """SkillOutput serializes correctly."""
    skill = SkillOutput(
        name="my-skill",
        path="my-skill",
        skill_md="---\nname: my-skill\n---\n\n# My Skill\n",
        references={"endpoints.md": "# Endpoints"},
        scripts={"setup.sh": "#!/bin/bash\necho hi"},
    )

    json_str = skill.model_dump_json()
    restored = SkillOutput.model_validate_json(json_str)
    assert restored.name == "my-skill"
    assert "endpoints.md" in restored.references


def test_generation_result():
    """GenerationResult holds skills and spec."""
    spec = APISpec(source="test", source_type="openapi", api_name="Test")
    result = GenerationResult(
        api_name="Test",
        skills=[
            SkillOutput(name="s1", path="s1", skill_md="test"),
        ],
        spec=spec,
    )
    assert len(result.skills) == 1
