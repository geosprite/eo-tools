from __future__ import annotations

import asyncio

from pydantic import Field

from geosprite.eo.catalog import ItemCollection, CatalogSearchRequest
from geosprite.eo.tools import Tool, ToolContext, tool

from . import catalog_service


class SearchSARRequest(CatalogSearchRequest):
    orbit_state: str | None = Field(default=None, description="Orbit direction, ascending or descending.")

@tool
class SearchSARTool(Tool[SearchSARRequest, ItemCollection]):
    name = "search.sar"
    version = "1.0.0"
    domain = "catalog"
    summary = "Search SAR imagery from STAC providers."
    description = "Search SAR collections and return a STAC FeatureCollection."
    InputModel = SearchSARRequest
    OutputModel = ItemCollection

    async def run(self, ctx: ToolContext, inputs: SearchSARRequest) -> ItemCollection:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: catalog_service.search(inputs))
