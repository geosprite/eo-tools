"""Helpers for tool discovery and registration."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from functools import partial
from pathlib import Path
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


_TOOL_CLASSES: list[type[Tool]] = []
_DISCOVERED_PACKAGES: set[tuple[str, str]] = set()

tool = partial(register_tool_class, _TOOL_CLASSES)


def discover_builtin_tools(
    *,
    package_name: str,
    package_file: str,
    excluded_modules: set[str] | None = None,
) -> list[Tool]:
    """Import builtin tool modules for a package and instantiate all registered tools."""

    package_key = (package_name, str(Path(package_file).resolve()))
    if package_key not in _DISCOVERED_PACKAGES:
        discover_tool_classes(
            package_name=package_name,
            package_file=package_file,
            classes=_TOOL_CLASSES,
            discovered=False,
            excluded_modules=excluded_modules,
        )
        _DISCOVERED_PACKAGES.add(package_key)
    return instantiate_tools(_TOOL_CLASSES)


def builtin_tools() -> list[Tool]:
    """Instantiate all globally registered builtin tools."""

    return instantiate_tools(_TOOL_CLASSES)


def build_builtin_registry(
    *,
    package_name: str | None = None,
    package_file: str | None = None,
    excluded_modules: set[str] | None = None,
) -> ToolRegistry:
    """Build a registry from the global builtin tool pool.

    When ``package_name`` and ``package_file`` are provided, that package is
    scanned before the registry is built.
    """

    if package_name is not None and package_file is not None:
        discover_builtin_tools(
            package_name=package_name,
            package_file=package_file,
            excluded_modules=excluded_modules,
        )
    return build_registry(builtin_tools())
