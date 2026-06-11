from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Iterable
from functools import partial
from importlib.metadata import entry_points
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar, cast

from .registry import ToolRegistry
from .tool import Tool

T = TypeVar("T", bound=type[Tool])
logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_MODULES = {"common", "core", "geometry", "registry"}
DEFAULT_ENTRY_POINT_GROUP = "geosprite.eo.tools"


_TOOL_CLASSES: list[type[Tool]] = []
_DISCOVERED_PACKAGES: set[tuple[str, str]] = set()


def _register_tool_class(classes: list[type[Tool]], cls: T) -> T:
    """Append a tool class to a package-local class list once."""
    tool_name = getattr(cls, "name", None)
    if cls not in classes and not any(getattr(existing, "name", None) == tool_name for existing in classes):
        classes.append(cls)
    return cls


tool = partial(_register_tool_class, _TOOL_CLASSES)


def _iter_compiled_modules(
    package_name: str,
    search_paths: Iterable[str],
    parent_parts: tuple[str, ...] = (),
    excluded: set[str] | None = None
) -> Iterable[str]:
    """Recursively scan for submodules in sourceless (compiled/packaged) environments."""
    for module_info in pkgutil.iter_modules(search_paths):
        parts = (*parent_parts, module_info.name)

        # Unified filtering: exclude __init__, blacklisted items, and modules ending with _common
        if parts[-1] == "__init__" or any(p in (excluded or set()) for p in parts) or any(
                p.endswith("_common") for p in parts):
            continue

        module_name = ".".join((package_name, *parts))
        if not module_info.ispkg:
            yield module_name
        else:
            # Only import the subpackage when encountered to retrieve its nested __path__
            try:
                subpackage = importlib.import_module(module_name)
                subpackage_paths = getattr(subpackage, "__path__", None)
                if subpackage_paths:
                    iterable_paths = cast(Iterable[str], subpackage_paths)
                    yield from _iter_compiled_modules(package_name, iterable_paths, parts, excluded)
            except ImportError:
                continue


def _iter_tool_modules(
    package_name: str,
    package_file: str,
    excluded_modules: set[str] | None = None
) -> Iterable[str]:
    """Dual-track module scanner: source mode preferred, fallback to compiled mode."""
    excluded = DEFAULT_EXCLUDED_MODULES | (excluded_modules or set())
    package_path = Path(package_file).resolve()
    source_dir: Path | None = None
    if package_path.is_dir():
        source_dir = package_path
    elif package_path.suffix == ".py":
        source_dir = package_path.parent

    # Track 1: Source mode (uses efficient Path scanning if .py files exist)
    py_files = sorted(source_dir.rglob("*.py")) if source_dir and source_dir.exists() else []
    if py_files:
        for module_file in py_files:
            relative_parts = module_file.relative_to(source_dir).with_suffix("").parts
            if relative_parts[-1] == "__init__" or any(p in excluded for p in relative_parts) or any(
                    p.endswith("_common") for p in relative_parts):
                continue
            yield ".".join((package_name, *relative_parts))
        return

    # Track 2: Compiled, sourceless, or packaged deployment mode (fallback)
    try:
        package = importlib.import_module(package_name)
        package_paths = getattr(package, "__path__", None)
        if package_paths:
            iterable_paths = cast(Iterable[str], package_paths)
            yield from _iter_compiled_modules(package_name, iterable_paths, excluded=excluded)
    except ImportError:
        return


def build_registry_from_package(
    package: str | ModuleType,
    package_file: str | None = None,
    *,
    excluded_modules: set[str] | None = None,
) -> ToolRegistry:
    """Discover, import, and build a ToolRegistry from a single target package."""

    # 1. Resolve package name and file path
    if isinstance(package, ModuleType):
        package_name = package.__name__
        resolved_file = getattr(package, "__file__", None)
    else:
        package_name = package
        resolved_file = package_file or getattr(importlib.import_module(package_name), "__file__", None)

    if resolved_file is None:
        raise ValueError(f"Package {package_name!r} does not expose a `__file__`.")

    # 2. Prevent duplicate scanning of the same package target
    package_key = (package_name, str(Path(resolved_file).resolve()))
    if package_key not in _DISCOVERED_PACKAGES:
        for module_name in _iter_tool_modules(package_name, resolved_file, excluded_modules):
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                logger.warning(f"Failed to import tool module {module_name!r}: {e}")
        _DISCOVERED_PACKAGES.add(package_key)

    # 3. Filter tool classes belonging to the current package, instantiate, and load into registry
    registry = ToolRegistry()
    for tool_cls in _TOOL_CLASSES:
        mod_name = getattr(tool_cls, "__module__", "")
        if mod_name == package_name or mod_name.startswith(f"{package_name}."):
            registry.register(tool_cls())

    return registry


def _coerce_registry_source(source: Any, source_name: str) -> ToolRegistry:
    """Coerce various loaded entry point object types into a standard ToolRegistry."""
    if isinstance(source, ToolRegistry):
        return source
    if isinstance(source, ModuleType):
        return build_registry_from_package(source)
    if callable(source):
        result = source()
        if isinstance(result, ToolRegistry):
            return result
        if isinstance(result, Iterable):
            registry = ToolRegistry()
            for t in result:
                registry.register(t)
            return registry

    raise TypeError(f"Entry point {source_name!r} returned an invalid type: {type(source).__name__}")


def build_registry_from_entry_points(group: str = DEFAULT_ENTRY_POINT_GROUP) -> ToolRegistry:
    """Discover installed tool packages from Python entry points and build a global registry."""
    discovered = entry_points(group=group)
    if not discovered:
        raise ValueError(f"No eo-tools entry points found in group {group!r}.")

    registry = ToolRegistry()
    for entry_point in discovered:
        source_registry = _coerce_registry_source(entry_point.load(), f"{entry_point.group}:{entry_point.name}")
        for tool_instance in source_registry:
            if tool_instance.name not in registry:
                registry.register(tool_instance)

    return registry
