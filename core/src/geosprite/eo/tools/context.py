"""Invocation context handed to tools at execution time.

Defined as a `Protocol` so tests can pass any duck-typed stub, and so the SDK
itself does not need to import storage or service packages.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolContext(Protocol):
    """Per-invocation context. Implementations live in host services."""

    # A storage facade supplied by the host service. Typed as `Any` so
    # `eo-tools` does not depend on a concrete storage package.
    store: Any
    workdir: Path
    logger: logging.Logger
    run_id: str | None
