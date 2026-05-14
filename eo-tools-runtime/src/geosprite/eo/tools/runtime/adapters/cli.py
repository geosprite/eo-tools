"""Command-line eo-tools-runtime for registered eo-tools."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from typing import Any

from ..core import (
    default_context_factory,
    describe_tool,
    dump_tool_output,
    execute_tool,
    load_registry,
)

from .mcp import main as mcp_main
from .rest import main as rest_main


def _add_tool_package_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tool-package",
        action="append",
        help=(
            "Import path for a tool package. "
            "When omitted, installed eo-tools entry points are discovered."
        ),
    )


def _load_arguments(args: argparse.Namespace) -> dict[str, Any]:
    if args.json is not None:
        return json.loads(args.json)
    if args.json_file is not None:
        with open(args.json_file, encoding="utf-8") as file:
            return json.load(file)
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)
    return {}


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


async def _run_tool(args: argparse.Namespace) -> None:
    registry = load_registry(args.tool_package)
    tool = registry.get(args.tool_name)
    output = await execute_tool(
        tool,
        default_context_factory()(args.run_id),
        _load_arguments(args),
    )
    _print_json(dump_tool_output(output))


def _list_tools(args: argparse.Namespace) -> None:
    registry = load_registry(args.tool_package)
    for tool in registry:
        print(tool.name)


def _describe_tool(args: argparse.Namespace) -> None:
    registry = load_registry(args.tool_package)
    _print_json(describe_tool(registry.get(args.tool_name)).model_dump(mode="json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eo-tools",
        description="Run and serve Earth Observation Tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List registered tools.")
    _add_tool_package_args(list_parser)

    describe_parser = subparsers.add_parser(
        "describe",
        help="Describe one registered tool.",
    )
    _add_tool_package_args(describe_parser)
    describe_parser.add_argument("tool_name")

    run_parser = subparsers.add_parser("run", help="Run one registered tool.")
    _add_tool_package_args(run_parser)
    run_parser.add_argument("tool_name")
    run_parser.add_argument("--json", help="Tool input as a JSON object.")
    run_parser.add_argument("--json-file", help="Path to a JSON input file.")
    run_parser.add_argument("--run-id")

    rest_parser = subparsers.add_parser(
        "serve-rest",
        help="Serve registered tools through FastAPI REST.",
    )
    _add_tool_package_args(rest_parser)
    rest_parser.add_argument("--host", default="127.0.0.1")
    rest_parser.add_argument("--port", default=8000, type=int)

    mcp_parser = subparsers.add_parser(
        "serve-mcp",
        help="Serve registered tools through MCP stdio.",
    )
    _add_tool_package_args(mcp_parser)
    mcp_parser.add_argument("--name", default="eo-tools")
    mcp_parser.add_argument("--version", default="0.1.0")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        _list_tools(args)
    elif args.command == "describe":
        _describe_tool(args)
    elif args.command == "run":
        asyncio.run(_run_tool(args))
    elif args.command == "serve-rest":
        rest_argv = [
            item
            for package in args.tool_package or ()
            for item in ("--tool-package", package)
        ]
        rest_argv.extend(["--host", args.host, "--port", str(args.port)])
        rest_main(rest_argv)
    elif args.command == "serve-mcp":
        mcp_argv = [
            item
            for package in args.tool_package or ()
            for item in ("--tool-package", package)
        ]
        mcp_argv.extend(["--name", args.name, "--version", args.version])
        mcp_main(mcp_argv)


if __name__ == "__main__":
    main()
