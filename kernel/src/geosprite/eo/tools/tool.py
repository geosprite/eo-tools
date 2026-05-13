"""Tool base class.

A `Tool` is the unit of capability exposed to Agents via MCP. Every tool
declares strongly-typed Pydantic models for input/output and an async `run`
method. Hosts route HTTP requests to `run`; OpenAPI/MCP tool descriptions are
generated from the docstring + Pydantic schemas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from .context import ToolContext

I = TypeVar("I", bound=BaseModel)  # noqa: E741 - input type
O = TypeVar("O", bound=BaseModel)  # noqa: E741 - output type


class Tool(ABC, Generic[I, O]):
    """Abstract base class for plugin tools.

    Subclasses must populate the class-level metadata fields and implement
    `run`. Use Pydantic models with rich field descriptions and examples; the
    descriptions are surfaced to LLMs via MCP, so they directly affect tool
    selection quality.
    """

    # ---- metadata (class-level; subclasses MUST override) -------------------
    name: ClassVar[str]
    """Globally unique tool name, e.g. `'compose.median'`."""

    version: ClassVar[str] = "0.1.0"
    """Semver version of the tool."""

    domain: ClassVar[str] = "general"
    """Coarse domain tag: `'preprocess' | 'postprocess' | 'ai' | 'compose' | ...`."""

    summary: ClassVar[str] = ""
    """One-line summary; surfaced as the MCP tool title."""

    description: ClassVar[str] = ""
    """Long description (LLM-targeted): purpose / inputs / outputs / examples."""

    requires: ClassVar[list[str]] = []
    """Capability hints, e.g. `['gpu']`, `['java']`, `['large_mem']`."""

    InputModel: ClassVar[type[BaseModel]]
    OutputModel: ClassVar[type[BaseModel]]

    # ---- behaviour ----------------------------------------------------------
    @abstractmethod
    async def run(self, ctx: ToolContext, inputs: I) -> O:
        """Execute the tool. Must be safe to call concurrently."""

    # ---- introspection helpers ---------------------------------------------
    @classmethod
    def fully_qualified_name(cls) -> str:
        return f"{cls.domain}.{cls.name}" if "." not in cls.name else cls.name
