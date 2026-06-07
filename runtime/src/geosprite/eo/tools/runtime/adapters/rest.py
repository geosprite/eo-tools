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
    store_context_factory,
)


def _import_fastapi() -> tuple[Any, Any, Any]:
    try:
        from fastapi import FastAPI, Header, HTTPException
    except ImportError as exc:
        raise ImportError(
            "FastAPI hosting requires optional dependencies. "
            "Install with `pip install -e runtime[rest]`."
        ) from exc
    return FastAPI, Header, HTTPException


def create_app(
    registry: ToolRegistry,
    *,
    title: str = "EO Tools REST API",
    version: str = "0.1.0",
    root_path: str = "",
    service_path: str = "",
    context_factory: ContextFactory | None = None,
):
    """Create a FastAPI app from a tool registry.

    The generated app exposes protocol-neutral registry endpoints plus one
    OpenAPI-typed endpoint for every tool.
    """

    FastAPI, Header, HTTPException = _import_fastapi()

    build_context = context_factory or default_context_factory()

    service_path = service_path.strip()
    if not service_path or service_path == "/":
        service_path = ""
    else:
        service_path = "/" + service_path.strip("/")

    docs_url = f"{service_path}/docs" if service_path else "/docs"
    openapi_url = f"{service_path}/openapi.json" if service_path else "/openapi.json"
    redoc_url = f"{service_path}/redoc" if service_path else "/redoc"

    app = FastAPI(
        title=title,
        version=version,
        root_path=root_path,
        docs_url=docs_url,
        openapi_url=openapi_url,
        redoc_url=redoc_url,
    )

    async def health() -> dict[str, str]:
        return {"status": "ok"}

    async def list_tools() -> list[dict[str, Any]]:
        return [describe_tool(_tool).model_dump(mode="json") for _tool in registry]

    async def get_tool(tool_name: str) -> dict[str, Any]:
        try:
            _tool = registry.get(tool_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return describe_tool(_tool).model_dump(mode="json")

    app.get("/health", include_in_schema=not service_path)(health)
    app.get("/", include_in_schema=not service_path)(list_tools)

    if service_path:
        app.get(f"{service_path}/health")(health)
        app.get(service_path, name="List tools")(list_tools)
        app.get(f"{service_path}/", include_in_schema=False)(list_tools)
        app.get(f"{service_path}/{{tool_name}}", name="Get tool")(get_tool)

    app.get("/{tool_name}", include_in_schema=not service_path)(get_tool)

    for tool in registry:
        _add_tool_route(app, tool, build_context, Header, HTTPException)

    return app


def _add_tool_route(
    app: Any,
    tool: Tool,
    context_factory: ContextFactory,
    header: Any,
    http_exception: Any,
) -> None:
    async def run_tool(
        inputs: Any,
        x_run_id: str | None = header(default=None),
    ) -> Any:
        try:
            output = await execute_tool(
                tool,
                context_factory(x_run_id),
                inputs.model_dump(mode="python"),
            )
        except Exception as exc:
            raise _tool_http_exception(exc, http_exception) from exc
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


def _tool_http_exception(exc: Exception, http_exception: Any) -> Exception:
    """Convert tool/runtime failures into JSON HTTP errors instead of ASGI 500s."""

    detail = str(exc) or exc.__class__.__name__
    return http_exception(status_code=500, detail=detail)


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
    parser.add_argument(
        "--root-path",
        default="",
        help=(
            "ASGI root path used when serving behind a path-prefix proxy, "
            "for example /eo-tools."
        ),
    )
    parser.add_argument(
        "--service-path",
        default="",
        help=(
            "Path inside the app for service-level endpoints such as docs, "
            "OpenAPI, health, and tool listing, for example /catalog."
        ),
    )
    parser.add_argument(
        "--workdir",
        help="Tool runtime workspace used for local outputs and staging.",
    )
    parser.add_argument(
        "--store-config",
        help=(
            "Optional JSON Store config. When omitted, the runtime uses the "
            "default Store if eo-store is installed."
        ),
    )
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "REST hosting requires uvicorn. Install with `pip install -e runtime[rest]`."
        ) from exc

    app = create_app(
        load_registry(args.tool_package),
        root_path=args.root_path,
        service_path=args.service_path,
        context_factory=store_context_factory(
            store_config=args.store_config,
            workdir=args.workdir,
        ),
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
