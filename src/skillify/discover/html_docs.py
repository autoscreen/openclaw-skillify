from __future__ import annotations

import re
from pathlib import Path

from skillify.discover.base import DiscoverySource
from skillify.llm.prompts import HTML_EXTRACTION_SYSTEM
from skillify.models import (
    APISpec,
    AuthSpec,
    AuthType,
    Endpoint,
    Parameter,
)
from skillify.util.fetcher import fetch_url


class HTMLDocsDiscovery(DiscoverySource):
    """AI-aided discovery from HTML or Markdown documentation."""

    async def can_handle(self, source: str) -> bool:
        source_lower = source.lower()
        # Markdown files
        if source_lower.endswith((".md", ".markdown", ".html", ".htm")):
            return Path(source).exists()
        # URLs that look like documentation
        if source_lower.startswith(("http://", "https://")):
            return True  # fallback — we'll try to extract from any URL
        return False

    async def discover(self, source: str) -> APISpec:
        text = await self._load_text(source)
        text = self._clean_text(text)

        # Truncate to avoid token limits
        max_chars = 50_000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[TRUNCATED]"

        from pydantic import BaseModel, Field

        class ExtractedAPI(BaseModel):
            api_name: str = "Unknown API"
            base_url: str | None = None
            auth: dict = Field(default_factory=dict)
            endpoints: list[dict] = Field(default_factory=list)

        source_hint = ""
        if source.startswith(("http://", "https://")):
            source_hint = (
                f"\n\nDocumentation source URL: {source}\n"
                "Note: This is the docs URL, NOT necessarily the API base URL. "
                "Extract the actual API base URL from the documentation content.\n"
            )

        result = await self.llm.structured_completion(
            system=HTML_EXTRACTION_SYSTEM,
            user=f"Extract API endpoints from this documentation:{source_hint}\n\n{text}",
            response_model=ExtractedAPI,
        )

        # Convert to our models
        auth = _parse_auth_dict(result.auth)
        endpoints = [_parse_endpoint_dict(ep) for ep in result.endpoints]

        return APISpec(
            source=source,
            source_type="html",
            api_name=result.api_name,
            base_url=result.base_url,
            auth=auth,
            endpoints=endpoints,
            raw_endpoint_count=len(endpoints),
        )

    async def _load_text(self, source: str) -> str:
        if source.startswith(("http://", "https://")):
            html = await fetch_url(source)
            return _html_to_text(html)
        text = Path(source).read_text()
        if source.lower().endswith((".html", ".htm")):
            return _html_to_text(text)
        return text

    def _clean_text(self, text: str) -> str:
        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text, stripping tags."""
    # Remove script and style elements
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace common block elements with newlines
    html = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode common entities
    html = html.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    html = html.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return html


def _parse_auth_dict(d: dict) -> AuthSpec:
    if not d:
        return AuthSpec()
    auth_type_map = {
        "bearer_token": AuthType.BEARER_TOKEN,
        "api_key_header": AuthType.API_KEY_HEADER,
        "api_key_query": AuthType.API_KEY_QUERY,
        "basic_auth": AuthType.BASIC_AUTH,
        "oauth2": AuthType.OAUTH2,
        "none": AuthType.NONE,
    }
    return AuthSpec(
        type=auth_type_map.get(d.get("type", "none"), AuthType.NONE),
        env_var=d.get("env_var"),
        header_name=d.get("header_name"),
        header_prefix=d.get("header_prefix"),
        description=d.get("description", ""),
    )


def _parse_endpoint_dict(d: dict) -> Endpoint:
    params = []
    for p in d.get("parameters", []):
        params.append(
            Parameter(
                name=p.get("name", ""),
                location=p.get("location", "query"),
                type=p.get("type", "string"),
                required=p.get("required", False),
                description=p.get("description", ""),
                example=p.get("example"),
            )
        )
    return Endpoint(
        method=d.get("method", "GET").upper(),
        path=d.get("path", "/"),
        summary=d.get("summary", ""),
        description=d.get("description", ""),
        parameters=params,
        tags=d.get("tags", []),
    )
