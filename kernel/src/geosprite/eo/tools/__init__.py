"""eo-tools: Earth Observation Tools protocol and registry."""

from pkgutil import extend_path

from .context import ToolContext
from .registry import ToolRegistry
from .tool import Tool, DictResultOut
from .discovery import (
    build_builtin_registry,
    build_registry,
    builtin_tools,
    discover_builtin_tools,
    discover_tool_classes,
    instantiate_tools,
    register_tool_class,
    tool,
)

__path__ = extend_path(__path__, __name__)

__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "DictResultOut",
    "build_builtin_registry",
    "build_registry",
    "builtin_tools",
    "discover_builtin_tools",
    "discover_tool_classes",
    "instantiate_tools",
    "register_tool_class",
    "tool",
]

__version__ = "0.1.0"
