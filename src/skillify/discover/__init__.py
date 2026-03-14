from __future__ import annotations

from pathlib import Path

from skillify.discover.base import DiscoverySource
from skillify.discover.openapi import OpenAPIDiscovery
from skillify.discover.graphql import GraphQLDiscovery
from skillify.discover.html_docs import HTMLDocsDiscovery
from skillify.discover.python_pkg import PythonPkgDiscovery
from skillify.discover.ai_analyzer import AIAnalyzer
from skillify.llm.client import SkillifyLLM
from skillify.models import APISpec

DISCOVERERS: list[type[DiscoverySource]] = [
    OpenAPIDiscovery,
    GraphQLDiscovery,
    PythonPkgDiscovery,
    HTMLDocsDiscovery,  # last because it's the most permissive
]


async def discover(
    source: str,
    source_type: str = "auto",
    model: str | None = None,
) -> APISpec:
    """Discover an API surface from the given source.

    Args:
        source: URL, file path, or Python package name.
        source_type: Force a specific source type, or "auto" to detect.
        model: LLM model for AI-aided discovery steps.

    Returns:
        An APISpec intermediate representation.
    """
    llm = SkillifyLLM(model=model)

    if source_type != "auto":
        discoverer = _get_discoverer_by_type(source_type, llm)
    else:
        discoverer = await _auto_detect(source, llm)

    spec = await discoverer.discover(source)

    # AI-aided grouping if groups not already populated
    if not spec.groups and spec.endpoints:
        analyzer = AIAnalyzer(llm)
        spec = await analyzer.group_and_enrich(spec)

    return spec


def _get_discoverer_by_type(source_type: str, llm: SkillifyLLM) -> DiscoverySource:
    """Get a discoverer by explicit type name."""
    mapping = {
        "openapi": OpenAPIDiscovery,
        "graphql": GraphQLDiscovery,
        "html": HTMLDocsDiscovery,
        "python": PythonPkgDiscovery,
    }
    cls = mapping.get(source_type)
    if not cls:
        raise ValueError(f"Unknown source type: {source_type}. Valid: {list(mapping)}")
    return cls(llm)


async def _auto_detect(source: str, llm: SkillifyLLM) -> DiscoverySource:
    """Auto-detect which discoverer to use."""
    for cls in DISCOVERERS:
        d = cls(llm)
        if await d.can_handle(source):
            return d
    raise ValueError(
        f"Could not auto-detect source type for: {source}. "
        f"Try specifying --source-type explicitly."
    )
