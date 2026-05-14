"""MCP adapter for exposing a ToolRegistry through Model Context Protocol."""

from __future__ import annotations

from collections.abc import Sequence
import argparse
import asyncio
from typing import Any

from geosprite.eo.tools import ToolRegistry

from ..core import (
    ContextFactory,
    default_context_factory,
    describe_tool,
    dump_tool_output,
    execute_tool,
    load_registry,
)


def _import_mcp() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import mcp.server.stdio
        import mcp.types as types
        from mcp.server.lowlevel import NotificationOptions, Server
        from mcp.server.models import InitializationOptions
    except ImportError as exc:
        raise ImportError(
            "MCP hosting requires optional dependencies. "
            "Install with `pip install -e eo-tools-runtime[mcp]`."
        ) from exc
    return mcp.server.stdio, types, NotificationOptions, Server, InitializationOptions


def create_server(
    registry: ToolRegistry,
    *,
    name: str = "eo-tools",
    context_factory: ContextFactory | None = None,
):
    """Create a low-level MCP server from a tool registry."""

    _stdio, types, _NotificationOptions, Server, _InitializationOptions = _import_mcp()
    build_context = context_factory or default_context_factory()
    server = Server(name)

    @server.list_tools()
    async def list_tools() -> list[Any]:
        return [
            types.Tool(
                name=tool.name,
                title=tool.summary or tool.name,
                description=tool.description or tool.summary,
                inputSchema=describe_tool(tool).input_schema,
                outputSchema=describe_tool(tool).output_schema,
            )
            for tool in registry
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = registry.get(name)
        output = await execute_tool(tool, build_context(None), arguments)
        return dump_tool_output(output)

    return server


async def run_stdio(
    registry: ToolRegistry,
    *,
    name: str = "eo-tools",
    version: str = "0.1.0",
    context_factory: ContextFactory | None = None,
) -> None:
    """Run a registry-backed MCP server over stdio."""

    stdio, _types, NotificationOptions, _Server, InitializationOptions = _import_mcp()
    server = create_server(registry, name=name, context_factory=context_factory)
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=name,
                server_version=version,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run eo-tools as an MCP stdio server."
    )
    parser.add_argument(
        "--tool-package",
        action="append",
        help=(
            "Import path for a tool package. "
            "When omitted, installed eo-tools entry points are discovered."
        ),
    )
    parser.add_argument("--name", default="eo-tools")
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args(argv)

    registry = load_registry(args.tool_package)
    asyncio.run(run_stdio(registry, name=args.name, version=args.version))


if __name__ == "__main__":
    main()
