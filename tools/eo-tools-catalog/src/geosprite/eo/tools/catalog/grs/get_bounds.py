from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from geosprite.eo.tools import Tool, ToolContext, DictResultOut, tool


class GetBoundsIn(BaseModel):
    system: Literal["mgrs", "wrs2"] = Field(description="Spatial grid system with bounds support.")
    tiles: list[str] = Field(description="Tile identifiers.")


@tool
class GetBoundsTool(Tool[GetBoundsIn, DictResultOut]):
    name = "bounds"
    version = "1.0.0"
    domain = "catalog.grs"
    summary = "Get bounds for spatial grid tiles."
    description = "Return bounding boxes for MGRS or WRS2 tile identifiers."
    InputModel = GetBoundsIn
    OutputModel = DictResultOut

    async def run(self, ctx: ToolContext, inputs: GetBoundsIn) -> DictResultOut:
        from geosprite.eo.catalog.grs import SpatialGrid

        grid = SpatialGrid(inputs.system)
        result: dict[str, Any] = {"bounds": grid.get_bounds(inputs.tiles)}
        return DictResultOut(result=result)
