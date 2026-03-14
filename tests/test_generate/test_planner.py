"""Tests for the generation planner."""
from skillify.generate.planner import Planner, SkillPlan
from skillify.models import (
    APISpec,
    AuthSpec,
    AuthType,
    Endpoint,
    EndpointGroup,
)


def _make_endpoints(n: int) -> list[Endpoint]:
    return [
        Endpoint(method="GET", path=f"/items/{i}", summary=f"Item {i}")
        for i in range(n)
    ]


def test_planner_inline_small_group():
    """Groups with <=8 endpoints should be inline."""
    spec = APISpec(
        source="test",
        source_type="openapi",
        api_name="Test",
        groups=[
            EndpointGroup(
                name="small-group",
                display_name="Small Group",
                description="A small group.",
                endpoints=_make_endpoints(5),
            )
        ],
    )
    plans = Planner().plan(spec)
    assert len(plans) == 1
    assert plans[0].inline_endpoints is True
    assert plans[0].needs_reference_file is False


def test_planner_reference_large_group():
    """Groups with >8 endpoints need a reference file."""
    spec = APISpec(
        source="test",
        source_type="openapi",
        api_name="Test",
        groups=[
            EndpointGroup(
                name="large-group",
                display_name="Large Group",
                description="A large group.",
                endpoints=_make_endpoints(15),
            )
        ],
    )
    plans = Planner().plan(spec)
    assert len(plans) == 1
    assert plans[0].inline_endpoints is False
    assert plans[0].needs_reference_file is True


def test_planner_oauth2_needs_script():
    """OAuth2 auth requires an auth setup script."""
    spec = APISpec(
        source="test",
        source_type="openapi",
        api_name="Test",
        auth=AuthSpec(type=AuthType.OAUTH2, env_var="OAUTH_TOKEN"),
        groups=[
            EndpointGroup(
                name="oauth-group",
                display_name="OAuth Group",
                description="Needs OAuth.",
                endpoints=_make_endpoints(3),
            )
        ],
    )
    plans = Planner().plan(spec)
    assert plans[0].needs_auth_script is True


def test_planner_bearer_no_script():
    """Bearer token auth does NOT require an auth script."""
    spec = APISpec(
        source="test",
        source_type="openapi",
        api_name="Test",
        auth=AuthSpec(type=AuthType.BEARER_TOKEN, env_var="API_TOKEN"),
        groups=[
            EndpointGroup(
                name="bearer-group",
                display_name="Bearer Group",
                description="Uses bearer.",
                endpoints=_make_endpoints(3),
            )
        ],
    )
    plans = Planner().plan(spec)
    assert plans[0].needs_auth_script is False
