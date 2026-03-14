from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import yaml

from skillify.discover.base import DiscoverySource
from skillify.models import (
    APISpec,
    AuthSpec,
    AuthType,
    Endpoint,
    EndpointGroup,
    Parameter,
)
from skillify.util.fetcher import fetch_url


class OpenAPIDiscovery(DiscoverySource):
    """Discover API from OpenAPI 3.x or Swagger 2.0 specs."""

    async def can_handle(self, source: str) -> bool:
        source_lower = source.lower()
        # File path checks
        if any(source_lower.endswith(ext) for ext in (".json", ".yaml", ".yml")):
            if Path(source).exists():
                try:
                    raw = Path(source).read_text()
                    doc = _parse_spec_text(raw)
                    return "openapi" in doc or "swagger" in doc
                except Exception:
                    return False
        # URL checks
        if source_lower.startswith(("http://", "https://")):
            if any(
                kw in source_lower
                for kw in ("openapi", "swagger", ".json", ".yaml", ".yml")
            ):
                return True
        return False

    async def discover(self, source: str) -> APISpec:
        raw_text = await self._load_source(source)
        doc = _parse_spec_text(raw_text)

        is_swagger2 = "swagger" in doc and str(doc.get("swagger", "")).startswith("2")
        if is_swagger2:
            return self._parse_swagger2(doc, source)
        return self._parse_openapi3(doc, source)

    async def _load_source(self, source: str) -> str:
        if source.startswith(("http://", "https://")):
            return await fetch_url(source)
        return Path(source).read_text()

    def _parse_openapi3(self, doc: dict, source: str) -> APISpec:
        info = doc.get("info", {})
        servers = doc.get("servers", [])
        base_url = servers[0]["url"] if servers else _infer_base_url_from_source(source)

        raw_title = info.get("title", "api")
        if _is_generic_title(raw_title):
            api_name = _infer_api_name_from_url(source) or "API"
        else:
            api_name = raw_title
        api_slug = _slugify(api_name)

        auth = self._extract_auth_v3(doc, api_name)
        endpoints = []
        tag_groups: dict[str, list[Endpoint]] = {}

        for path, path_item in doc.get("paths", {}).items():
            path_item = self._resolve_refs(path_item, doc)
            for method in ("get", "post", "put", "patch", "delete", "head", "options"):
                if method not in path_item:
                    continue
                op = path_item[method]
                op = self._resolve_refs(op, doc)
                ep = self._parse_operation_v3(method, path, op, doc)
                endpoints.append(ep)
                for tag in ep.tags or ["default"]:
                    tag_groups.setdefault(tag, []).append(ep)

        # Build groups from tags
        groups = []
        for tag, eps in tag_groups.items():
            name = f"{api_slug}-{_slugify(tag)}"
            groups.append(
                EndpointGroup(
                    name=name,
                    display_name=tag.replace("_", " ").title(),
                    description=f"Interact with {tag} endpoints of the {api_name}.",
                    endpoints=eps,
                    tags=[tag],
                )
            )

        return APISpec(
            source=source,
            source_type="openapi",
            api_name=api_name,
            api_description=info.get("description", ""),
            base_url=base_url,
            version=info.get("version"),
            auth=auth,
            endpoints=endpoints,
            groups=groups,
            raw_endpoint_count=len(endpoints),
        )

    def _parse_swagger2(self, doc: dict, source: str) -> APISpec:
        info = doc.get("info", {})
        host = doc.get("host", "")
        base_path = doc.get("basePath", "")
        schemes = doc.get("schemes", ["https"])
        base_url = f"{schemes[0]}://{host}{base_path}" if host else _infer_base_url_from_source(source)

        raw_title = info.get("title", "api")
        if _is_generic_title(raw_title):
            api_name = _infer_api_name_from_url(source) or "API"
        else:
            api_name = raw_title
        api_slug = _slugify(api_name)

        auth = self._extract_auth_v2(doc, api_name)
        endpoints = []
        tag_groups: dict[str, list[Endpoint]] = {}

        for path, path_item in doc.get("paths", {}).items():
            path_item = self._resolve_refs(path_item, doc)
            for method in ("get", "post", "put", "patch", "delete", "head", "options"):
                if method not in path_item:
                    continue
                op = path_item[method]
                op = self._resolve_refs(op, doc)
                ep = self._parse_operation_v2(method, path, op, doc)
                endpoints.append(ep)
                for tag in ep.tags or ["default"]:
                    tag_groups.setdefault(tag, []).append(ep)

        groups = []
        for tag, eps in tag_groups.items():
            name = f"{api_slug}-{_slugify(tag)}"
            groups.append(
                EndpointGroup(
                    name=name,
                    display_name=tag.replace("_", " ").title(),
                    description=f"Interact with {tag} endpoints of the {api_name}.",
                    endpoints=eps,
                    tags=[tag],
                )
            )

        return APISpec(
            source=source,
            source_type="openapi",
            api_name=api_name,
            api_description=info.get("description", ""),
            base_url=base_url,
            version=info.get("version"),
            auth=auth,
            endpoints=endpoints,
            groups=groups,
            raw_endpoint_count=len(endpoints),
        )

    def _parse_operation_v3(
        self, method: str, path: str, op: dict, doc: dict
    ) -> Endpoint:
        params = []
        for p in op.get("parameters", []):
            p = self._resolve_refs(p, doc)
            params.append(
                Parameter(
                    name=p.get("name", ""),
                    location=p.get("in", "query"),
                    type=_schema_type(p.get("schema", {})),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                    example=str(p.get("example", "")) if p.get("example") else None,
                )
            )

        request_body = op.get("requestBody")
        request_body_schema = None
        if request_body:
            request_body = self._resolve_refs(request_body, doc)
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            request_body_schema = self._resolve_refs(
                json_content.get("schema", {}), doc
            )

        response_schema = None
        responses = op.get("responses", {})
        for code in ("200", "201", "default"):
            if code in responses:
                resp = self._resolve_refs(responses[code], doc)
                content = resp.get("content", {})
                json_content = content.get("application/json", {})
                if "schema" in json_content:
                    response_schema = self._resolve_refs(
                        json_content["schema"], doc
                    )
                    break

        return Endpoint(
            method=method.upper(),
            path=path,
            summary=op.get("summary", ""),
            description=op.get("description", ""),
            parameters=params,
            request_body_schema=request_body_schema,
            response_schema=response_schema,
            tags=op.get("tags", []),
        )

    def _parse_operation_v2(
        self, method: str, path: str, op: dict, doc: dict
    ) -> Endpoint:
        params = []
        for p in op.get("parameters", []):
            p = self._resolve_refs(p, doc)
            if p.get("in") == "body":
                continue  # handled separately
            params.append(
                Parameter(
                    name=p.get("name", ""),
                    location=p.get("in", "query"),
                    type=p.get("type", "string"),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                )
            )

        # Body parameter in Swagger 2
        request_body_schema = None
        for p in op.get("parameters", []):
            p = self._resolve_refs(p, doc)
            if p.get("in") == "body":
                request_body_schema = self._resolve_refs(
                    p.get("schema", {}), doc
                )
                break

        response_schema = None
        responses = op.get("responses", {})
        for code in ("200", "201", "default"):
            if code in responses:
                resp = self._resolve_refs(responses[code], doc)
                if "schema" in resp:
                    response_schema = self._resolve_refs(resp["schema"], doc)
                    break

        return Endpoint(
            method=method.upper(),
            path=path,
            summary=op.get("summary", ""),
            description=op.get("description", ""),
            parameters=params,
            request_body_schema=request_body_schema,
            response_schema=response_schema,
            tags=op.get("tags", []),
        )

    def _extract_auth_v3(self, doc: dict, api_name: str | None = None) -> AuthSpec:
        components = doc.get("components", {})
        schemes = components.get("securitySchemes", {})
        return self._auth_from_schemes(schemes, api_name)

    def _extract_auth_v2(self, doc: dict, api_name: str | None = None) -> AuthSpec:
        schemes = doc.get("securityDefinitions", {})
        return self._auth_from_schemes(schemes, api_name)

    def _auth_from_schemes(self, schemes: dict, api_name: str | None = None) -> AuthSpec:
        if not schemes:
            return AuthSpec()

        # Pick the first scheme
        name, scheme = next(iter(schemes.items()))
        scheme_type = scheme.get("type", "")

        if scheme_type == "http":
            http_scheme = scheme.get("scheme", "").lower()
            if http_scheme == "bearer":
                return AuthSpec(
                    type=AuthType.BEARER_TOKEN,
                    env_var=_suggest_env_var(name, api_name),
                    header_name="Authorization",
                    header_prefix="Bearer",
                    description=scheme.get("description", "Bearer token authentication"),
                )
            if http_scheme == "basic":
                return AuthSpec(
                    type=AuthType.BASIC_AUTH,
                    description=scheme.get("description", "Basic authentication"),
                )

        if scheme_type == "apiKey":
            location = scheme.get("in", "header")
            param_name = scheme.get("name", "X-API-Key")
            if location == "header":
                return AuthSpec(
                    type=AuthType.API_KEY_HEADER,
                    env_var=_suggest_env_var(name, api_name),
                    header_name=param_name,
                    description=scheme.get("description", f"API key in {param_name} header"),
                )
            return AuthSpec(
                type=AuthType.API_KEY_QUERY,
                env_var=_suggest_env_var(name, api_name),
                description=scheme.get("description", f"API key as query parameter: {param_name}"),
            )

        if scheme_type == "oauth2":
            return AuthSpec(
                type=AuthType.OAUTH2,
                env_var=_suggest_env_var(name, api_name),
                description=scheme.get("description", "OAuth2 authentication"),
            )

        return AuthSpec()

    def _resolve_refs(self, obj: dict | list, doc: dict, depth: int = 10) -> dict | list:
        """Resolve $ref references in an OpenAPI document."""
        if depth <= 0:
            return obj
        if isinstance(obj, list):
            return [self._resolve_refs(item, doc, depth - 1) for item in obj]
        if not isinstance(obj, dict):
            return obj
        if "$ref" in obj:
            ref_path = obj["$ref"]
            resolved = self._follow_ref(ref_path, doc)
            if resolved is not None:
                return self._resolve_refs(resolved, doc, depth - 1)
            return obj
        return {k: self._resolve_refs(v, doc, depth - 1) for k, v in obj.items()}

    def _follow_ref(self, ref: str, doc: dict) -> dict | None:
        """Follow a JSON pointer reference like #/components/schemas/Pet."""
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        current = doc
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current


def _parse_spec_text(text: str) -> dict:
    """Parse a spec from JSON or YAML text."""
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    return yaml.safe_load(text)


def _slugify(text: str) -> str:
    """Convert text to a lowercase hyphenated slug."""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _schema_type(schema: dict) -> str:
    """Extract a simple type string from a JSON Schema."""
    return schema.get("type", "string")


_GENERIC_TITLES = frozenset({
    "fastapi", "api", "swagger", "openapi", "rest api", "my api",
    "server", "app", "application", "unknown api", "default", "",
})


def _is_generic_title(title: str) -> bool:
    """Return True if the title is a framework default or too generic."""
    return title.strip().lower() in _GENERIC_TITLES


def _infer_api_name_from_url(source: str) -> str | None:
    """Infer a human-readable API name from a URL.

    e.g. "https://api.yutori.com/openapi.json" -> "Yutori API"
    """
    if not source.startswith(("http://", "https://")):
        return None
    parsed = urlparse(source)
    hostname = parsed.hostname or ""
    parts = hostname.split(".")
    ignore = {"www", "api", "docs", "dev", "staging", "com", "org", "net", "io", "co", "app"}
    meaningful = [p for p in parts if p.lower() not in ignore and len(p) > 1]
    if not meaningful and len(parts) >= 2:
        meaningful = [parts[-2]]
    if not meaningful:
        return None
    name = meaningful[0].capitalize()
    return f"{name} API"


def _infer_base_url_from_source(source: str) -> str | None:
    """Infer a base URL from the source URL by stripping the spec filename."""
    if not source.startswith(("http://", "https://")):
        return None
    parsed = urlparse(source)
    path = parsed.path
    if "/" in path and path != "/":
        last_segment = path.rsplit("/", 1)[-1].lower()
        if any(last_segment.endswith(ext) for ext in (".json", ".yaml", ".yml")):
            path = path.rsplit("/", 1)[0]
    base = f"{parsed.scheme}://{parsed.netloc}{path}"
    return base.rstrip("/") or f"{parsed.scheme}://{parsed.netloc}"


_GENERIC_SCHEME_NAMES = frozenset({
    "apikeyauth", "apikey", "api_key", "bearerauth", "bearer",
    "httpbearer", "http_bearer", "oauth2", "basicauth", "basic",
    "authorization", "auth", "security", "token",
})


def _suggest_env_var(name: str, api_name: str | None = None) -> str:
    """Suggest an environment variable name from a security scheme name.

    If the scheme name is generic and api_name is provided, uses the
    api_name for a more descriptive variable name.
    """
    import re

    normalized = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
    if normalized in _GENERIC_SCHEME_NAMES and api_name:
        base = re.sub(r"\s*api\s*$", "", api_name, flags=re.IGNORECASE).strip()
        base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").upper()
        if base:
            name = base

    # Split camelCase/PascalCase
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"[^a-zA-Z0-9]", "_", name).upper()
    name = re.sub(r"_+", "_", name).strip("_")

    if not name.endswith(("_KEY", "_TOKEN", "_SECRET")):
        name += "_API_KEY"
    return name
