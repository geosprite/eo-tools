from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from geosprite.eo.tools import Tool, ToolContext
from geosprite.eo.tools.catalog.grs import SpatialGrid

from .common import DictResultOut
from .registry import catalog_tool

class SpatialTilesIn(BaseModel):
    system: Literal["mgrs", "wgrs", "wrs2"] = Field(description="Spatial grid system.")
    geojson: str = Field(description="GeoJSON geometry string.")


@catalog_tool
class SpatialTilesTool(Tool[SpatialTilesIn, DictResultOut]):
    name = "catalog.spatial_tiles"
    version = "1.0.0"
    domain = "catalog"
    summary = "Find spatial grid tiles covering a GeoJSON geometry."
    description = "Return MGRS, WGRS, or WRS2 tile identifiers for the input geometry."
    InputModel = SpatialTilesIn
    OutputModel = DictResultOut

    async def run(self, ctx: ToolContext, inputs: SpatialTilesIn) -> DictResultOut:
        grid = SpatialGrid(inputs.system)
        result: dict[str, Any] = {key: value for tiles in grid.get_tiles(inputs.geojson) for key, value in tiles.items()}
        return DictResultOut(result=result)
