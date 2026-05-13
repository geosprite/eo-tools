from __future__ import annotations

from pydantic import BaseModel

from geosprite.eo.tools import Tool, ToolContext, tool

from .core import SpatialGridFactory


class GetSystemsIn(BaseModel):
    pass


class GetSystemsOut(BaseModel):
    systems: list[str]


@tool
class SpatialSystemsTool(Tool[GetSystemsIn, GetSystemsOut]):
    name = "catalog.get_grs_systems"
    version = "1.0.0"
    domain = "catalog"
    summary = "List available spatial grid systems."
    description = "Return the spatial grid systems registered in catalog."
    InputModel = GetSystemsIn
    OutputModel = GetSystemsOut

    async def run(self, ctx: ToolContext, inputs: GetSystemsIn) -> GetSystemsOut:
        return GetSystemsOut(systems=SpatialGridFactory.get_systems())
