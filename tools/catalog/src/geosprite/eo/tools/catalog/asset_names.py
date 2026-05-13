from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import Tool, ToolContext

from .common import DictResultOut, get_catalog_client
from .registry import catalog_tool

class AssetNamesIn(BaseModel):
    collection: str = Field(description="STAC collection name.")
    provider: str | None = Field(default=None, description="Provider override: element84 or planetarycomputer.")


@catalog_tool
class AssetNamesTool(Tool[AssetNamesIn, DictResultOut]):
    name = "catalog.asset_names"
    version = "1.0.0"
    domain = "catalog"
    summary = "List available asset names for a STAC collection."
    description = "Return provider asset metadata for the requested collection."
    InputModel = AssetNamesIn
    OutputModel = DictResultOut

    async def run(self, ctx: ToolContext, inputs: AssetNamesIn) -> DictResultOut:
        loop = asyncio.get_running_loop()
        result: dict[str, Any] = await loop.run_in_executor(
            None,
            lambda: get_catalog_client(inputs.provider).get_asset_names(inputs.collection),
        )
        return DictResultOut(result=result)
