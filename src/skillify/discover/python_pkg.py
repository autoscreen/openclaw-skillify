from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path
from types import ModuleType

from skillify.discover.base import DiscoverySource
from skillify.models import APISpec, Endpoint, Parameter


class PythonPkgDiscovery(DiscoverySource):
    """Discover API from a Python package's public interface."""

    async def can_handle(self, source: str) -> bool:
        # Matches if it looks like a Python module name
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", source):
            try:
                importlib.import_module(source)
                return True
            except ImportError:
                return False
        return False

    async def discover(self, source: str) -> APISpec:
        mod = importlib.import_module(source)
        endpoints = self._extract_from_module(mod, source)

        return APISpec(
            source=source,
            source_type="python",
            api_name=_module_display_name(source),
            api_description=inspect.getdoc(mod) or "",
            endpoints=endpoints,
            raw_endpoint_count=len(endpoints),
        )

    def _extract_from_module(self, mod: ModuleType, prefix: str) -> list[Endpoint]:
        endpoints = []

        for name, obj in inspect.getmembers(mod):
            if name.startswith("_"):
                continue

            if inspect.isclass(obj) and obj.__module__ == mod.__name__:
                endpoints.extend(self._extract_from_class(obj, prefix))
            elif inspect.isfunction(obj) and obj.__module__ == mod.__name__:
                ep = self._function_to_endpoint(obj, prefix, name)
                if ep:
                    endpoints.append(ep)

        return endpoints

    def _extract_from_class(self, cls: type, prefix: str) -> list[Endpoint]:
        endpoints = []
        class_name = cls.__name__
        tag = class_name.lower()

        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_") and name != "__init__":
                continue

            ep = self._function_to_endpoint(
                method, f"{prefix}.{class_name}", name, tag=tag
            )
            if ep:
                endpoints.append(ep)

        return endpoints

    def _function_to_endpoint(
        self,
        func,
        module_path: str,
        name: str,
        tag: str | None = None,
    ) -> Endpoint | None:
        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            return None

        doc = inspect.getdoc(func) or ""
        summary = doc.split("\n")[0] if doc else name

        params = []
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            type_str = "string"
            if param.annotation != inspect.Parameter.empty:
                type_str = _annotation_to_type(param.annotation)
            required = param.default is inspect.Parameter.empty
            params.append(
                Parameter(
                    name=param_name,
                    location="body",
                    type=type_str,
                    required=required,
                    description="",
                )
            )

        # Map to pseudo-REST endpoint
        method = _infer_method(name)
        path = f"/{module_path.replace('.', '/')}/{name}"

        return Endpoint(
            method=method,
            path=path,
            summary=summary,
            description=doc,
            parameters=params,
            tags=[tag] if tag else [module_path.split(".")[-1]],
        )


def _annotation_to_type(annotation) -> str:
    """Convert a Python type annotation to a simple type string."""
    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation)


def _infer_method(name: str) -> str:
    """Infer HTTP method from function name."""
    name_lower = name.lower()
    if name_lower.startswith(("get", "list", "fetch", "read", "find", "search")):
        return "GET"
    if name_lower.startswith(("create", "add", "insert", "post", "new")):
        return "POST"
    if name_lower.startswith(("update", "edit", "modify", "patch")):
        return "PATCH"
    if name_lower.startswith(("delete", "remove", "destroy")):
        return "DELETE"
    if name_lower.startswith(("set", "put", "replace")):
        return "PUT"
    return "POST"


def _module_display_name(module_name: str) -> str:
    """Generate a display name from a module name."""
    parts = module_name.split(".")
    return parts[0].replace("_", " ").title()
