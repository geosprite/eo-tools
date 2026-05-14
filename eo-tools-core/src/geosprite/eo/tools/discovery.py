"""Helpers for tool discovery and registration."""

from __future__ import annotations

import importlib
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
    if cls not in classes and not any(
        getattr(existing, "name", None) == tool_name for existing in classes
    ):
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

    for module_file in sorted(package_dir.rglob("*.py")):
        relative_module = module_file.relative_to(package_dir).with_suffix("")
        parts = relative_module.parts
        if (
            parts[-1] == "__init__"
            or any(part in excluded for part in parts)
            or any(part.endswith("_common") for part in parts)
        ):
            continue
        yield ".".join((package_name, *parts))


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


def build_registry_from_modules(module_names: Iterable[str]) -> ToolRegistry:
    """Discover tools from registry modules and build one combined registry.

    Each module is expected to expose ``discover_builtin_tools`` or
    ``build_builtin_registry``. Tool packages in this repo expose both from
    their package-local ``registry.py`` modules.
    """

    module_registries: list[ToolRegistry] = []
    for module_name in module_names:
        module = importlib.import_module(module_name)
        discover = getattr(module, "discover_builtin_tools", None)
        if discover is not None:
            discover()
            continue

        build = getattr(module, "build_builtin_registry", None)
        if build is not None:
            module_registries.append(build())
            continue

        raise AttributeError(
            f"Registry module {module_name!r} must expose "
            "`discover_builtin_tools` or `build_builtin_registry`."
        )

    registry = build_builtin_registry()
    for module_registry in module_registries:
        for tool_instance in module_registry:
            if tool_instance.name not in registry:
                registry.register(tool_instance)
    return registry
