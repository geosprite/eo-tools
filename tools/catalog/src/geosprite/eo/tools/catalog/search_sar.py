from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from geosprite.eo.stac import ItemCollection
from geosprite.eo.tools import Tool, ToolContext

from .common import execute_search
from .registry import catalog_tool

_SAR_QUERY_FIELDS = {"datetime", "bbox", "geometry", "tile", "orbit_state"}


class SearchSARIn(BaseModel):
    collection: str = Field(description="SAR STAC collection, for example sentinel-1-rtc or sentinel-1-grd.")
    datetime: str = Field(description="Date range such as 2024-01-01/2024-02-01, or an instant datetime.")
    bbox: str | None = Field(default=None, description="Bounding box as minx,miny,maxx,maxy.")
    geometry: str | None = Field(default=None, description="GeoJSON geometry string.")
    tile: str | None = Field(default=None, description="MGRS tile ID.")
    orbit_state: str | None = Field(default=None, description="Orbit direction, ascending or descending.")
    provider: str | None = Field(default=None, description="Provider override: element84 or planetarycomputer.")


@catalog_tool
class SearchSARTool(Tool[SearchSARIn, ItemCollection]):
    name = "catalog.search_sar"
    version = "1.0.0"
    domain = "catalog"
    summary = "Search SAR imagery from STAC providers."
    description = "Search SAR collections and return a STAC FeatureCollection."
    InputModel = SearchSARIn
    OutputModel = ItemCollection

    async def run(self, ctx: ToolContext, inputs: SearchSARIn) -> ItemCollection:
        raw = inputs.model_dump(exclude_none=True)
        collection = raw.pop("collection")
        provider = raw.pop("provider", None)
        query_kwargs = {key: value for key, value in raw.items() if key in _SAR_QUERY_FIELDS}
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: execute_search(collection, query_kwargs, provider))
