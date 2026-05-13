from __future__ import annotations

from geosprite.eo.tools.catalog.grs import SpatialGridFactory
from geosprite.eo.tools import Tool, ToolContext
from pydantic import BaseModel

from .registry import catalog_tool


class SpatialSystemsIn(BaseModel):
    pass


class SpatialSystemsOut(BaseModel):
    systems: list[str]


@catalog_tool
class SpatialSystemsTool(Tool[SpatialSystemsIn, SpatialSystemsOut]):
    name = "catalog.spatial_systems"
    version = "1.0.0"
    domain = "catalog"
    summary = "List available spatial grid systems."
    description = "Return the spatial grid systems registered in catalog."
    InputModel = SpatialSystemsIn
    OutputModel = SpatialSystemsOut

    async def run(self, ctx: ToolContext, inputs: SpatialSystemsIn) -> SpatialSystemsOut:
        return SpatialSystemsOut(systems=SpatialGridFactory.get_systems())
