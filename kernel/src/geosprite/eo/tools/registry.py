"""In-memory tool registry."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import logging

from .tool import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """A simple name-to-tool mapping. Hosts construct one per process."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not getattr(tool, "name", None):
            raise ValueError(f"Tool {type(tool).__name__} is missing `name`.")
        if tool.name in self._tools:
            raise ValueError(
                f"Duplicate tool name {tool.name!r}: "
                f"already registered as {type(self._tools[tool.name]).__name__}."
            )
        self._tools[tool.name] = tool
        logger.info("Registered tool %r (%s)", tool.name, type(tool).__name__)

    def register_many(self, tools: Iterable[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool {name!r} not found") from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._tools

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)
