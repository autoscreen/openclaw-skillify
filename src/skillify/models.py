from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AuthType(str, Enum):
    NONE = "none"
    API_KEY_HEADER = "api_key_header"
    API_KEY_QUERY = "api_key_query"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class AuthSpec(BaseModel):
    """Authentication requirements for an API."""

    type: AuthType = AuthType.NONE
    env_var: str | None = None
    header_name: str | None = None
    header_prefix: str | None = None
    description: str = ""


class Parameter(BaseModel):
    """A single endpoint parameter."""

    name: str
    location: str = "query"  # query, path, header, body
    type: str = "string"
    required: bool = False
    description: str = ""
    example: str | None = None


class Endpoint(BaseModel):
    """A single API endpoint."""

    method: str
    path: str
    summary: str = ""
    description: str = ""
    parameters: list[Parameter] = Field(default_factory=list)
    request_body_schema: dict | None = None
    response_schema: dict | None = None
    tags: list[str] = Field(default_factory=list)
    examples: list[dict] = Field(default_factory=list)


class EndpointGroup(BaseModel):
    """A logical group of endpoints that maps to one skill."""

    name: str
    display_name: str
    description: str
    endpoints: list[Endpoint]
    auth: AuthSpec | None = None
    tags: list[str] = Field(default_factory=list)


class APISpec(BaseModel):
    """Complete intermediate representation of a discovered API.

    This is the contract between discover() and generate().
    Serializable to/from JSON for caching and manual editing.
    """

    source: str
    source_type: str  # openapi, graphql, html, python
    api_name: str
    api_description: str = ""
    base_url: str | None = None
    version: str | None = None
    auth: AuthSpec = Field(default_factory=AuthSpec)
    endpoints: list[Endpoint] = Field(default_factory=list)
    groups: list[EndpointGroup] = Field(default_factory=list)
    raw_endpoint_count: int = 0


class SkillOutput(BaseModel):
    """Represents a generated skill directory."""

    name: str
    path: str
    skill_md: str
    references: dict[str, str] = Field(default_factory=dict)
    scripts: dict[str, str] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class GenerationResult(BaseModel):
    """Complete output of the generate pipeline."""

    api_name: str
    skills: list[SkillOutput]
    spec: APISpec
