from __future__ import annotations

from abc import ABC, abstractmethod

from skillify.llm.client import SkillifyLLM
from skillify.models import APISpec


class DiscoverySource(ABC):
    """Base class for API discovery sources."""

    def __init__(self, llm: SkillifyLLM):
        self.llm = llm

    @abstractmethod
    async def can_handle(self, source: str) -> bool:
        """Return True if this discoverer can handle the given source."""
        ...

    @abstractmethod
    async def discover(self, source: str) -> APISpec:
        """Discover API surface from the source and return an APISpec."""
        ...
