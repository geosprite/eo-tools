from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.stac import GenericStacApiClient, ItemCollection
from geosprite.eo.tools import Tool, ToolContext, tool


class SearchStacIn(BaseModel):
    stac_url: str = Field(description="STAC API root URL.")
    collections: list[str] | None = None
    ids: list[str] | None = None
    datetime: str | None = None
    bbox: list[float] | None = None
    intersects: dict[str, Any] | None = None
    query: dict[str, Any] | None = None
    filter: dict[str, Any] | str | None = None
    limit: int | None = Field(default=None, ge=1)
    token: str | None = Field(default=None, description="Optional bearer token for protected STAC APIs.")


@tool
class SearchStacTool(Tool[SearchStacIn, ItemCollection]):
    name = "search"
    version = "1.0.0"
    domain = "catalog"
    summary = "Search any STAC API."
    description = "Searches an arbitrary STAC API URL and returns a STAC FeatureCollection."
    InputModel = SearchStacIn
    OutputModel = ItemCollection

    async def run(self, ctx: ToolContext, inputs: SearchStacIn) -> ItemCollection:
        payload = inputs.model_dump(exclude_none=True)
        stac_url = payload.pop("stac_url")
        token = payload.pop("token", None)
        client = GenericStacApiClient(stac_url, token=token)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: client.search(payload))
