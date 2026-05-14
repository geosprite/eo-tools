"""Context factory helpers shared by eo-tools-runtime adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any

from geosprite.eo.tools import ToolContext

ContextFactory = Callable[[str | None], ToolContext]


@dataclass(slots=True)
class LocalToolContext:
    """Minimal context implementation for local hosts and smoke tests."""

    store: Any = None
    workdir: Path = field(default_factory=Path.cwd)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("geosprite.eo.tools")
    )
    run_id: str | None = None


def default_context_factory(
    *,
    store: object = None,
    workdir: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> ContextFactory:
    """Create a per-request context factory for simple local hosts."""

    resolved_workdir = Path.cwd() if workdir is None else Path(workdir)
    resolved_logger = logger or logging.getLogger("geosprite.eo.tools.eo-tools-runtime")

    def build_context(run_id: str | None = None) -> ToolContext:
        return LocalToolContext(
            store=store,
            workdir=resolved_workdir,
            logger=resolved_logger,
            run_id=run_id,
        )

    return build_context
