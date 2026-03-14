"""Tests for OpenAPI discovery."""
import pytest

from skillify.discover.openapi import OpenAPIDiscovery
from skillify.llm.client import SkillifyLLM
from skillify.models import AuthType


@pytest.fixture
def discoverer():
    llm = SkillifyLLM.__new__(SkillifyLLM)
    llm.model = "test"
    return OpenAPIDiscovery(llm)


@pytest.mark.asyncio
async def test_can_handle_json_file(discoverer, petstore_spec_path):
    assert await discoverer.can_handle(str(petstore_spec_path))


@pytest.mark.asyncio
async def test_can_handle_rejects_random(discoverer):
    assert not await discoverer.can_handle("random_string")


@pytest.mark.asyncio
async def test_discover_petstore(discoverer, petstore_spec_path):
    spec = await discoverer.discover(str(petstore_spec_path))

    assert spec.api_name == "Petstore API"
    assert spec.source_type == "openapi"
    assert spec.base_url == "https://petstore.example.com/v1"
    assert spec.version == "1.0.0"

    # Should have 9 endpoints total (5 pets + 4 store)
    assert spec.raw_endpoint_count == 9

    # Should have 2 groups from tags
    assert len(spec.groups) == 2
    group_names = {g.name for g in spec.groups}
    assert "petstore-api-pets" in group_names
    assert "petstore-api-store" in group_names


@pytest.mark.asyncio
async def test_discover_petstore_auth(discoverer, petstore_spec_path):
    spec = await discoverer.discover(str(petstore_spec_path))

    assert spec.auth.type == AuthType.BEARER_TOKEN
    assert spec.auth.header_name == "Authorization"
    assert spec.auth.header_prefix == "Bearer"


@pytest.mark.asyncio
async def test_discover_petstore_endpoints(discoverer, petstore_spec_path):
    spec = await discoverer.discover(str(petstore_spec_path))

    # Find the list pets endpoint
    list_pets = next(
        (e for e in spec.endpoints if e.path == "/pets" and e.method == "GET"),
        None,
    )
    assert list_pets is not None
    assert list_pets.summary == "List all pets"
    assert len(list_pets.parameters) == 2

    limit_param = next(p for p in list_pets.parameters if p.name == "limit")
    assert limit_param.type == "integer"
    assert limit_param.required is False


@pytest.mark.asyncio
async def test_discover_petstore_ref_resolution(discoverer, petstore_spec_path):
    spec = await discoverer.discover(str(petstore_spec_path))

    # Create pet should have resolved $ref in request body
    create_pet = next(
        (e for e in spec.endpoints if e.path == "/pets" and e.method == "POST"),
        None,
    )
    assert create_pet is not None
    assert create_pet.request_body_schema is not None
    # The $ref should be resolved to the actual Pet schema
    assert "properties" in create_pet.request_body_schema
