"""Helpers for package-local tool discovery.

Tool component packages can keep tiny local registries while sharing the module
scanning and ToolRegistry construction logic here.
"""

from __future__ import annotations

from collections.abc import Iterable
import importlib
from pathlib import Path
import pkgutil
from typing import TypeVar

from .registry import ToolRegistry
from .tool import Tool

T = TypeVar("T", bound=type[Tool])

DEFAULT_EXCLUDED_MODULES = {"common", "core", "geometry", "registry"}


def register_tool_class(classes: list[type[Tool]], cls: T) -> T:
    """Append a tool class to a package-local class list once."""
    tool_name = getattr(cls, "name", None)
    if cls not in classes and not any(getattr(existing, "name", None) == tool_name for existing in classes):
        classes.append(cls)
    return cls


def iter_tool_modules(
    *,
    package_name: str,
    package_file: str,
    excluded_modules: set[str] | None = None,
) -> Iterable[str]:
    """Yield importable module names under a package that may contain tools."""
    package_dir = Path(package_file).resolve().parent
    excluded = DEFAULT_EXCLUDED_MODULES | (excluded_modules or set())

    for module in pkgutil.walk_packages([str(package_dir)], prefix=f"{package_name}."):
        short_name = module.name.rsplit(".", 1)[-1]
        if module.ispkg or short_name in excluded or short_name.endswith("_common"):
            continue
        yield module.name


def discover_tool_classes(
    *,
    package_name: str,
    package_file: str,
    classes: list[type[Tool]],
    discovered: bool,
    excluded_modules: set[str] | None = None,
) -> bool:
    """Import candidate modules once so decorators can populate ``classes``."""
    if discovered:
        return True
    for module_name in sorted(
        iter_tool_modules(
            package_name=package_name,
            package_file=package_file,
            excluded_modules=excluded_modules,
        )
    ):
        importlib.import_module(module_name)
    return True


def instantiate_tools(classes: Iterable[type[Tool]]) -> list[Tool]:
    """Create fresh tool instances from registered classes."""
    return [tool_cls() for tool_cls in classes]


def build_registry(tools: Iterable[Tool]) -> ToolRegistry:
    """Build a ToolRegistry from discovered tool instances."""
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry
