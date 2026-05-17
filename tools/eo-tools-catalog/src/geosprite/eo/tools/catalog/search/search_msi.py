from __future__ import annotations

import asyncio

from geosprite.eo.catalog import ItemCollection, CatalogSearchRequest
from geosprite.eo.tools import Tool, ToolContext, tool

from . import catalog_service


@tool
class SearchMSITool(Tool[CatalogSearchRequest, ItemCollection]):
    name = "search.msi"
    version = "1.0.0"
    domain = "catalog"
    summary = "Search multispectral imagery from STAC providers."
    description = "Search MSI collections and return a STAC FeatureCollection with selected assets."
    InputModel = CatalogSearchRequest
    OutputModel = ItemCollection

    async def run(self, ctx: ToolContext, inputs: CatalogSearchRequest) -> ItemCollection:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: catalog_service.search(inputs))
