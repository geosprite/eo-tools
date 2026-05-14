"""FastAPI adapter for exposing a ToolRegistry as REST endpoints."""

from __future__ import annotations

from collections.abc import Sequence
import argparse
from typing import Any

from geosprite.eo.tools import Tool, ToolRegistry

from ..core import (
    ContextFactory,
    default_context_factory,
    describe_tool,
    execute_tool,
    load_registry,
)


def _import_fastapi() -> tuple[Any, Any, Any]:
    try:
        from fastapi import FastAPI, Header, HTTPException
    except ImportError as exc:
        raise ImportError(
            "FastAPI hosting requires optional dependencies. "
            "Install with `pip install -e eo-tools-runtime[rest]`."
        ) from exc
    return FastAPI, Header, HTTPException


def create_app(
    registry: ToolRegistry,
    *,
    title: str = "EO Tools REST API",
    version: str = "0.1.0",
    context_factory: ContextFactory | None = None,
):
    """Create a FastAPI app from a tool registry.

    The generated app exposes protocol-neutral registry endpoints plus one
    OpenAPI-typed endpoint for every tool.
    """

    FastAPI, Header, HTTPException = _import_fastapi()
    build_context = context_factory or default_context_factory()
    app = FastAPI(title=title, version=version)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def list_tools() -> list[dict[str, Any]]:
        return [describe_tool(tool).model_dump(mode="json") for tool in registry]

    @app.get("/{tool_name}")
    async def get_tool(tool_name: str) -> dict[str, Any]:
        try:
            tool = registry.get(tool_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return describe_tool(tool).model_dump(mode="json")

    for tool in registry:
        _add_tool_route(app, tool, build_context, Header)

    return app


def _add_tool_route(
    app: Any,
    tool: Tool,
    context_factory: ContextFactory,
    Header: Any,
) -> None:
    async def run_tool(
        inputs: Any,
        x_run_id: str | None = Header(default=None),
    ) -> Any:
        output = await execute_tool(
            tool,
            context_factory(x_run_id),
            inputs.model_dump(mode="python"),
        )
        return output

    run_tool.__name__ = f"run_{tool.name.replace('.', '_')}"
    run_tool.__doc__ = tool.description or tool.summary
    run_tool.__annotations__ = {
        "inputs": tool.InputModel,
        "x_run_id": str | None,
        "return": tool.OutputModel,
    }

    tool_route_path = f"/{tool.domain.replace('.', '/')}/{tool.name.replace('.', '/')}"
    tool_route_name = f"Run {tool.name} in the domain '{tool.domain}'"

    app.post(
        tool_route_path,
        name=tool_route_name,
        summary=tool.summary or tool_route_name,
        description=tool.description or None,
        response_model=tool.OutputModel,
    )(run_tool)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run Earth Observation Tools (eo-tools) as a FastAPI REST service."
    )
    parser.add_argument(
        "--tool-package",
        action="append",
        help=(
            "Import path for a tool package. "
            "When omitted, installed eo-tools entry points are discovered."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "REST hosting requires uvicorn. Install with `pip install -e eo-tools-runtime[rest]`."
        ) from exc

    app = create_app(load_registry(args.tool_package))
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
