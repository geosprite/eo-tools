"""Tool registry loading helpers for runtime adapters."""

from __future__ import annotations

from collections.abc import Iterable

from geosprite.eo.tools import ToolRegistry, build_registry_from_modules


def load_registry(registry_modules: Iterable[str]) -> ToolRegistry:
    """Load one combined ToolRegistry from tool package registry modules."""

    return build_registry_from_modules(registry_modules)
