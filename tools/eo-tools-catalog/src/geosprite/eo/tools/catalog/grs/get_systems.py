from __future__ import annotations

from pydantic import BaseModel

from geosprite.eo.tools import Tool, ToolContext, tool


class GetSystemsIn(BaseModel):
    pass


class GetSystemsOut(BaseModel):
    systems: list[str]


@tool
class SpatialSystemsTool(Tool[GetSystemsIn, GetSystemsOut]):
    name = "systems"
    version = "1.0.0"
    domain = "catalog.grs"
    summary = "List available spatial grid systems."
    description = "Return the spatial grid systems registered in catalog."
    InputModel = GetSystemsIn
    OutputModel = GetSystemsOut

    async def run(self, ctx: ToolContext, inputs: GetSystemsIn) -> GetSystemsOut:
        from geosprite.eo.catalog.grs import SpatialGridFactory

        return GetSystemsOut(systems=SpatialGridFactory.get_systems())
