from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from geosprite.eo.catalog import ItemCollection
from geosprite.eo.tools import Tool, ToolContext, tool

from .__init__ import execute_search

_MSI_QUERY_FIELDS = {"datetime", "bbox", "geometry", "tile", "assets", "cloud_cover", "nodata_percent"}


class SearchMSIIn(BaseModel):
    collection: str = Field(description="MSI STAC collection, for example sentinel-2-l2a or landsat-c2-l2.")
    datetime: str = Field(description="Date range such as 2024-01-01/2024-02-01, or an instant datetime.")
    bbox: str | None = Field(default=None, description="Bounding box as minx,miny,maxx,maxy.")
    geometry: str | None = Field(default=None, description="GeoJSON geometry string.")
    tile: str | None = Field(default=None, description="MGRS tile ID.")
    assets: list[str] | None = Field(default=None, description="Asset names to include.")
    cloud_cover: str | None = Field(default=None, description="Maximum cloud cover percentage.")
    nodata_percent: str | None = Field(default=None, description="Maximum no-data percentage.")
    provider: str | None = Field(default=None, description="Provider override: element84 or planetarycomputer.")


@tool
class SearchMSITool(Tool[SearchMSIIn, ItemCollection]):
    name = "search.msi"
    version = "1.0.0"
    domain = "catalog"
    summary = "Search multispectral imagery from STAC providers."
    description = "Search MSI collections and return a STAC FeatureCollection with selected assets."
    InputModel = SearchMSIIn
    OutputModel = ItemCollection

    async def run(self, ctx: ToolContext, inputs: SearchMSIIn) -> ItemCollection:
        raw = inputs.model_dump(exclude_none=True)
        collection = raw.pop("collection")
        provider = raw.pop("provider", None)
        query_kwargs = {key: value for key, value in raw.items() if key in _MSI_QUERY_FIELDS}
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: execute_search(collection, query_kwargs, provider))
