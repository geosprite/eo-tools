from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from geosprite.eo.tools import Tool, ToolContext, DictResultOut, tool


class GetTilesIn(BaseModel):
    system: Literal["mgrs", "wgrs", "wrs2"] = Field(description="Spatial grid system.")
    geojson: str = Field(description="GeoJSON geometry string.")


@tool
class GetTilesTool(Tool[GetTilesIn, DictResultOut]):
    name = "tiles"
    version = "1.0.0"
    domain = "catalog.grs"
    summary = "Find spatial grid tiles covering a GeoJSON geometry."
    description = "Return MGRS, WGRS, or WRS2 tile identifiers for the input geometry."
    InputModel = GetTilesIn
    OutputModel = DictResultOut

    async def run(self, ctx: ToolContext, inputs: GetTilesIn) -> DictResultOut:
        from geosprite.eo.catalog.grs import SpatialGrid

        grid = SpatialGrid(inputs.system)
        result: dict[str, Any] = {key: value for tiles in grid.get_tiles(inputs.geojson) for key, value in tiles.items()}
        return DictResultOut(result=result)
