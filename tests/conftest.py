from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def petstore_spec_path():
    return FIXTURES / "petstore_openapi.json"


@pytest.fixture
def petstore_spec_text(petstore_spec_path):
    return petstore_spec_path.read_text()
