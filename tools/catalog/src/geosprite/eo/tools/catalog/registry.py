from __future__ import annotations

from geosprite.eo.tools import (
    Tool,
    ToolRegistry,
    build_builtin_registry as _build_builtin_registry,
    discover_builtin_tools as _discover_builtin_tools,
    tool,
)

catalog_tool = tool


def discover_builtin_tools() -> list[Tool]:
    """Import every catalog builtin tool module and instantiate registered tools."""
    return _discover_builtin_tools(
        package_name=__package__ or "geosprite.eo.tools.catalog",
        package_file=__file__,
    )


def builtin_tools() -> list[Tool]:
    """Backward-compatible alias for automatic builtin discovery."""
    return discover_builtin_tools()


def build_builtin_registry() -> ToolRegistry:
    return _build_builtin_registry(
        package_name=__package__ or "geosprite.eo.tools.catalog",
        package_file=__file__,
    )
