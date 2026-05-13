from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.stac import Asset, Item, build_item_from_assets
from geosprite.eo.tools import Tool, ToolContext, tool

from .core.stac_api import GenericStacApiClient

class PublishItemIn(BaseModel):
    stac_url: str = Field(description="Target STAC API root URL, for example http://localhost:8080.")
    collection: str = Field(description="Target STAC collection id.")
    item: Item | None = Field(default=None, description="Complete STAC Item payload.")
    item_id: str | None = Field(default=None, description="Item id when building from assets.")
    datetime: str | None = Field(default=None, description="STAC item datetime.")
    geometry: dict[str, Any] | None = None
    bbox: list[float] | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Asset] = Field(default_factory=dict)
    upsert: bool = True
    token: str | None = Field(default=None, description="Optional bearer token for protected STAC APIs.")


@tool
class PublishItemTool(Tool[PublishItemIn, Item]):
    name = "catalog.publish_item"
    version = "1.0.0"
    domain = "catalog"
    summary = "Create or update an item in a STAC API."
    description = "Publishes a processing/model result Item through STAC API transaction endpoints."
    InputModel = PublishItemIn
    OutputModel = Item

    async def run(self, ctx: ToolContext, inputs: PublishItemIn) -> Item:
        item = inputs.item or self._build_item(inputs)
        if item.collection is None:
            item.collection = inputs.collection
        client = GenericStacApiClient(inputs.stac_url, token=inputs.token)
        loop = asyncio.get_running_loop()
        if inputs.upsert:
            return await loop.run_in_executor(None, lambda: client.upsert_item(inputs.collection, item))
        return await loop.run_in_executor(None, lambda: client.create_item(inputs.collection, item))

    @staticmethod
    def _build_item(inputs: PublishItemIn) -> Item:
        if not inputs.item_id:
            raise ValueError("item_id is required when item is not provided")
        if not inputs.assets:
            raise ValueError("assets is required when item is not provided")
        return build_item_from_assets(
            item_id=inputs.item_id,
            collection=inputs.collection,
            assets=inputs.assets,
            geometry=inputs.geometry,
            bbox=inputs.bbox,
            properties=inputs.properties,
            datetime_value=inputs.datetime,
        )
