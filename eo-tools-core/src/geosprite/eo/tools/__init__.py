"""eo-tools: Earth Observation Tools protocol and registry."""

from pkgutil import extend_path

from .context import ToolContext
from .registry import ToolRegistry
from .tool import Tool, DictResultOut
from .discovery import (
    DEFAULT_ENTRY_POINT_GROUP,
    build_registry_from_entry_points,
    build_registry_from_package,
    tool,
)

__path__ = extend_path(__path__, __name__)

__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "DictResultOut",
    "DEFAULT_ENTRY_POINT_GROUP",
    "build_registry_from_entry_points",
    "build_registry_from_package",
    "tool",
]

__version__ = "0.1.0"
