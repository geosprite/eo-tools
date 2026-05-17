"""Shared tool metadata and execution helpers for runtime adapters."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import Tool, ToolContext


class ToolDescriptor(BaseModel):
    """Protocol-neutral metadata for a registered tool."""

    name: str
    version: str
    domain: str
    summary: str
    description: str
    requires: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


def model_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a JSON schema suitable for OpenAPI and MCP tool metadata."""

    return model.model_json_schema()


def describe_tool(tool: Tool) -> ToolDescriptor:
    """Build protocol-neutral metadata from a tool instance."""

    return ToolDescriptor(
        name=tool.name,
        version=tool.version,
        domain=tool.domain,
        summary=tool.summary,
        description=tool.description,
        requires=list(tool.requires),
        input_schema=model_json_schema(tool.InputModel),
        output_schema=model_json_schema(tool.OutputModel),
    )


async def execute_tool(
    tool: Tool,
    ctx: ToolContext,
    arguments: dict[str, Any] | None,
) -> BaseModel:
    """Validate raw arguments, run a tool, and validate the output model."""

    inputs = tool.InputModel.model_validate(arguments or {})
    output = await tool.run(ctx, inputs)
    return tool.OutputModel.model_validate(output)


def dump_tool_output(output: BaseModel) -> dict[str, Any]:
    """Convert a Pydantic tool output into JSON-compatible data."""

    return output.model_dump(mode="json")
