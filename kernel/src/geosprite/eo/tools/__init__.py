"""eo-tools: Earth Observation Tools protocol and registry."""

from pkgutil import extend_path

from .context import ToolContext
from .discovery import (
    build_registry,
    discover_tool_classes,
    instantiate_tools,
    register_tool_class,
)
from .registry import ToolRegistry
from .tool import Tool

__path__ = extend_path(__path__, __name__)

__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "build_registry",
    "discover_tool_classes",
    "instantiate_tools",
    "register_tool_class",
]

__version__ = "0.1.0"
