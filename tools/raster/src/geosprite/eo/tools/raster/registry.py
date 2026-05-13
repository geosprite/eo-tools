from __future__ import annotations

from typing import TypeVar

from geosprite.eo.tools import (
    Tool,
    ToolRegistry,
    build_registry,
    discover_tool_classes,
    instantiate_tools,
    register_tool_class,
)

T = TypeVar("T", bound=type[Tool])

_TOOL_CLASSES: list[type[Tool]] = []
_DISCOVERED = False


def raster_tool(cls: T) -> T:
    """Register a builtin raster Tool class when its module is imported."""
    return register_tool_class(_TOOL_CLASSES, cls)


def discover_builtin_tools() -> list[Tool]:
    """Import every raster builtin tool module and instantiate registered tools."""
    global _DISCOVERED
    _DISCOVERED = discover_tool_classes(
        package_name=__package__ or "geosprite.eo.tools.raster",
        package_file=__file__,
        classes=_TOOL_CLASSES,
        discovered=_DISCOVERED,
    )
    return instantiate_tools(_TOOL_CLASSES)


def builtin_tools() -> list[Tool]:
    """Backward-compatible alias for automatic builtin discovery."""
    return discover_builtin_tools()


def build_builtin_registry() -> ToolRegistry:
    return build_registry(discover_builtin_tools())
