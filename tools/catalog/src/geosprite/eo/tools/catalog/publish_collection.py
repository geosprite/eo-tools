from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.stac import Collection, build_collection
from geosprite.eo.tools import Tool, ToolContext

from .registry import catalog_tool
from .stac_api import GenericStacApiClient

class PublishCollectionIn(BaseModel):
    stac_url: str = Field(description="Target STAC API root URL, for example http://localhost:8080.")
    collection: Collection | None = Field(default=None, description="Complete STAC Collection payload.")
    collection_id: str | None = Field(default=None, description="Collection id when building a minimal payload.")
    description: str | None = Field(default=None, description="Collection description when building a minimal payload.")
    title: str | None = None
    license: str = "proprietary"
    spatial_bbox: list[float] | None = Field(default=None, description="Collection spatial bbox.")
    temporal_interval: list[str | None] | None = Field(default=None, description="Collection temporal interval.")
    keywords: list[str] | None = None
    providers: list[dict[str, Any]] | None = None
    summaries: dict[str, Any] | None = None
    item_assets: dict[str, dict[str, Any]] | None = None
    upsert: bool = True
    token: str | None = Field(default=None, description="Optional bearer token for protected STAC APIs.")


@catalog_tool
class PublishCollectionTool(Tool[PublishCollectionIn, Collection]):
    name = "catalog.publish_collection"
    version = "1.0.0"
    domain = "catalog"
    summary = "Create or update a collection in a STAC API."
    description = "Publishes a STAC Collection through STAC API transaction endpoints."
    InputModel = PublishCollectionIn
    OutputModel = Collection

    async def run(self, ctx: ToolContext, inputs: PublishCollectionIn) -> Collection:
        collection = inputs.collection or self._build_collection(inputs)
        client = GenericStacApiClient(inputs.stac_url, token=inputs.token)
        loop = asyncio.get_running_loop()
        if inputs.upsert:
            return await loop.run_in_executor(None, lambda: client.upsert_collection(collection))
        return await loop.run_in_executor(None, lambda: client.create_collection(collection))

    @staticmethod
    def _build_collection(inputs: PublishCollectionIn) -> Collection:
        if not inputs.collection_id:
            raise ValueError("collection_id is required when collection is not provided")
        if not inputs.description:
            raise ValueError("description is required when collection is not provided")
        return build_collection(
            collection_id=inputs.collection_id,
            title=inputs.title,
            description=inputs.description,
            license=inputs.license,
            spatial_bbox=inputs.spatial_bbox,
            temporal_interval=inputs.temporal_interval,
            keywords=inputs.keywords,
            providers=inputs.providers,
            summaries=inputs.summaries,
            item_assets=inputs.item_assets,
        )
