"""Context factory helpers shared by runtime adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any

from geosprite.eo.tools import ToolContext

ContextFactory = Callable[[str | None], ToolContext]


@dataclass(slots=True)
class RuntimeToolContext:
    """Default runtime context implementation for local hosts and smoke tests."""

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
    resolved_logger = logger or logging.getLogger("geosprite.eo.tools.runtime")

    def build_context(run_id: str | None = None) -> ToolContext:
        return RuntimeToolContext(
            store=store,
            workdir=resolved_workdir,
            logger=resolved_logger,
            run_id=run_id,
        )

    return build_context


def store_context_factory(
    *,
    store_config: str | Path | None = None,
    workdir: str | Path | None = None,
    logger: logging.Logger | None = None,
) -> ContextFactory:
    """Create a local context factory with Store support when available."""

    if store_config is not None:
        try:
            from geosprite.eo.store import Store
        except ImportError as exc:
            raise ImportError(
                "Store config support requires `eo-store`. "
                "Install `eo-tools-runtime[store]` or install `eo-store`."
            ) from exc
        store = Store.with_config(store_config)
    else:
        store = _default_store_if_available()

    return default_context_factory(store=store, workdir=workdir, logger=logger)


def _default_store_if_available() -> object | None:
    try:
        from geosprite.eo.store import Store
    except ImportError:
        return None

    return Store.with_defaults()
