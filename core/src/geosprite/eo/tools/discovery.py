"""Helpers for tool discovery and registration."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from functools import partial
from importlib.metadata import entry_points
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from .registry import ToolRegistry
from .tool import Tool

T = TypeVar("T", bound=type[Tool])

DEFAULT_EXCLUDED_MODULES = {"common", "core", "geometry", "registry"}
DEFAULT_ENTRY_POINT_GROUP = "geosprite.eo.tools"


def _register_tool_class(classes: list[type[Tool]], cls: T) -> T:
    """Append a tool class to a package-local class list once."""
    tool_name = getattr(cls, "name", None)
    if cls not in classes and not any(
        getattr(existing, "name", None) == tool_name for existing in classes
    ):
        classes.append(cls)
    return cls


def _iter_tool_modules(
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


def _discover_tool_classes(
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
        _iter_tool_modules(
            package_name=package_name,
            package_file=package_file,
            excluded_modules=excluded_modules,
        )
    ):
        importlib.import_module(module_name)
    return True


def _instantiate_tools(classes: Iterable[type[Tool]]) -> list[Tool]:
    """Create fresh tool instances from registered classes."""
    return [tool_cls() for tool_cls in classes]


def _build_registry(tools: Iterable[Tool]) -> ToolRegistry:
    """Build a ToolRegistry from discovered tool instances."""
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


_TOOL_CLASSES: list[type[Tool]] = []
_DISCOVERED_PACKAGES: set[tuple[str, str]] = set()

tool = partial(_register_tool_class, _TOOL_CLASSES)


def _resolve_package(
    package: str | ModuleType,
    package_file: str | None = None,
) -> tuple[str, str]:
    if isinstance(package, ModuleType):
        package_name = package.__name__
        resolved_file = getattr(package, "__file__", None)
    else:
        package_name = package
        resolved_file = package_file
        if resolved_file is None:
            resolved_file = getattr(
                importlib.import_module(package_name),
                "__file__",
                None,
            )

    if resolved_file is None:
        raise ValueError(f"Package {package_name!r} does not expose a `__file__`.")
    return package_name, resolved_file


def _is_tool_class_in_package(tool_cls: type[Tool], package_name: str) -> bool:
    module_name = getattr(tool_cls, "__module__", "")
    return module_name == package_name or module_name.startswith(f"{package_name}.")


def _discover_package_classes(
    *,
    package_name: str,
    package_file: str,
    excluded_modules: set[str] | None = None,
) -> list[type[Tool]]:
    package_key = (package_name, str(Path(package_file).resolve()))
    if package_key not in _DISCOVERED_PACKAGES:
        _discover_tool_classes(
            package_name=package_name,
            package_file=package_file,
            classes=_TOOL_CLASSES,
            discovered=False,
            excluded_modules=excluded_modules,
        )
        _DISCOVERED_PACKAGES.add(package_key)
    return [
        tool_cls
        for tool_cls in _TOOL_CLASSES
        if _is_tool_class_in_package(tool_cls, package_name)
    ]


def _discover_package_tools(
    package: str | ModuleType,
    package_file: str | None = None,
    *,
    excluded_modules: set[str] | None = None,
) -> list[Tool]:
    """Import one tool package and instantiate only tools defined under it."""

    package_name, resolved_file = _resolve_package(package, package_file)
    return _instantiate_tools(
        _discover_package_classes(
            package_name=package_name,
            package_file=resolved_file,
            excluded_modules=excluded_modules,
        )
    )


def build_registry_from_package(
    package: str | ModuleType,
    package_file: str | None = None,
    *,
    excluded_modules: set[str] | None = None,
) -> ToolRegistry:
    """Build a ToolRegistry from one package-scoped discovery target."""

    return _build_registry(
        _discover_package_tools(
            package,
            package_file,
            excluded_modules=excluded_modules,
        )
    )


def _coerce_registry_source(source: Any, *, source_name: str) -> ToolRegistry:
    """Build a ToolRegistry from an entry point target."""

    if isinstance(source, ToolRegistry):
        return source

    if isinstance(source, ModuleType):
        return build_registry_from_package(source)

    if callable(source):
        result = source()
        if isinstance(result, ToolRegistry):
            return result
        if isinstance(result, Iterable):
            return _build_registry(result)

    raise TypeError(
        f"Entry point {source_name!r} must load a ToolRegistry, a callable "
        "returning a ToolRegistry or tools, or a tool package module."
    )


def build_registry_from_entry_points(
    group: str = DEFAULT_ENTRY_POINT_GROUP,
) -> ToolRegistry:
    """Discover installed tool packages from Python entry points."""

    discovered = entry_points(group=group)
    if not discovered:
        raise ValueError(
            f"No eo-tools entry points found in group {group!r}. "
            "Install an eo-tools plugin package that declares this entry point group."
        )

    registry = ToolRegistry()
    for entry_point in discovered:
        source_registry = _coerce_registry_source(
            entry_point.load(),
            source_name=f"{entry_point.group}:{entry_point.name}",
        )
        for tool_instance in source_registry:
            if tool_instance.name not in registry:
                registry.register(tool_instance)
    return registry
