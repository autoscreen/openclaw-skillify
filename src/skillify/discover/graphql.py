from __future__ import annotations

from pathlib import Path

from skillify.discover.base import DiscoverySource
from skillify.models import APISpec, AuthSpec, Endpoint, Parameter
from skillify.util.fetcher import fetch_url

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name kind description
      fields {
        name description
        args { name description type { name kind ofType { name kind } } }
        type { name kind ofType { name kind } }
      }
    }
  }
}
"""


class GraphQLDiscovery(DiscoverySource):
    """Discover API from a GraphQL endpoint or schema file."""

    async def can_handle(self, source: str) -> bool:
        source_lower = source.lower()
        if source_lower.endswith((".graphql", ".gql")):
            return Path(source).exists()
        if source_lower.startswith(("http://", "https://")):
            return "graphql" in source_lower
        return False

    async def discover(self, source: str) -> APISpec:
        if source.startswith(("http://", "https://")):
            return await self._discover_from_endpoint(source)
        return self._discover_from_file(source)

    async def _discover_from_endpoint(self, url: str) -> APISpec:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json={"query": INTROSPECTION_QUERY},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        schema = data.get("data", {}).get("__schema", {})
        return self._parse_introspection(schema, url)

    def _discover_from_file(self, path: str) -> APISpec:
        text = Path(path).read_text()
        endpoints = self._parse_sdl(text)
        return APISpec(
            source=path,
            source_type="graphql",
            api_name=Path(path).stem.replace("_", " ").title(),
            endpoints=endpoints,
            raw_endpoint_count=len(endpoints),
        )

    def _parse_introspection(self, schema: dict, source: str) -> APISpec:
        query_type_name = (schema.get("queryType") or {}).get("name", "Query")
        mutation_type_name = (schema.get("mutationType") or {}).get("name", "Mutation")

        endpoints = []
        types_map = {t["name"]: t for t in schema.get("types", [])}

        for type_name, method_prefix in [
            (query_type_name, "GET"),
            (mutation_type_name, "POST"),
        ]:
            type_def = types_map.get(type_name, {})
            for field in type_def.get("fields", []):
                params = []
                for arg in field.get("args", []):
                    arg_type = _resolve_type(arg.get("type", {}))
                    params.append(
                        Parameter(
                            name=arg["name"],
                            location="body",
                            type=arg_type,
                            required="!" in arg_type,
                            description=arg.get("description", ""),
                        )
                    )

                return_type = _resolve_type(field.get("type", {}))
                tag = "query" if method_prefix == "GET" else "mutation"

                endpoints.append(
                    Endpoint(
                        method=method_prefix,
                        path=f"/graphql#{field['name']}",
                        summary=field.get("description", field["name"]),
                        description=field.get("description", ""),
                        parameters=params,
                        tags=[tag],
                    )
                )

        return APISpec(
            source=source,
            source_type="graphql",
            api_name="GraphQL API",
            endpoints=endpoints,
            raw_endpoint_count=len(endpoints),
        )

    def _parse_sdl(self, text: str) -> list[Endpoint]:
        """Basic SDL parsing — extracts type Query and type Mutation fields."""
        import re

        endpoints = []
        # Find type blocks
        for match in re.finditer(
            r"type\s+(Query|Mutation)\s*\{([^}]+)\}", text, re.DOTALL
        ):
            type_name = match.group(1)
            method = "GET" if type_name == "Query" else "POST"
            tag = type_name.lower()
            body = match.group(2)

            for field_match in re.finditer(
                r"(\w+)(?:\(([^)]*)\))?\s*:\s*(\S+)", body
            ):
                name = field_match.group(1)
                args_str = field_match.group(2) or ""
                return_type = field_match.group(3)

                params = []
                if args_str.strip():
                    for arg in args_str.split(","):
                        arg = arg.strip()
                        parts = arg.split(":")
                        if len(parts) == 2:
                            params.append(
                                Parameter(
                                    name=parts[0].strip(),
                                    location="body",
                                    type=parts[1].strip(),
                                    required="!" in parts[1],
                                )
                            )

                endpoints.append(
                    Endpoint(
                        method=method,
                        path=f"/graphql#{name}",
                        summary=name,
                        parameters=params,
                        tags=[tag],
                    )
                )

        return endpoints


def _resolve_type(type_obj: dict) -> str:
    """Resolve a GraphQL introspection type to a string."""
    kind = type_obj.get("kind", "")
    name = type_obj.get("name")
    if name:
        return name
    of_type = type_obj.get("ofType", {})
    if kind == "NON_NULL":
        return f"{_resolve_type(of_type)}!"
    if kind == "LIST":
        return f"[{_resolve_type(of_type)}]"
    return of_type.get("name", "Unknown")
