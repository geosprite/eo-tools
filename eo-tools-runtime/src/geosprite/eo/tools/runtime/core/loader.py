"""Tool registry loading helpers for runtime adapters."""

from __future__ import annotations

from collections.abc import Iterable

from geosprite.eo.tools import (
    ToolRegistry,
    build_registry_from_entry_points,
    build_registry_from_package,
)


def load_registry(tool_packages: Iterable[str] | None = None) -> ToolRegistry:
    """Load one combined ToolRegistry from packages or installed entry points."""

    if tool_packages:
        registry = ToolRegistry()
        for package in tool_packages:
            package_registry = build_registry_from_package(package)
            for tool in package_registry:
                if tool.name not in registry:
                    registry.register(tool)
        return registry

    return build_registry_from_entry_points()
