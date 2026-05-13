from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import Tool, ToolContext
from geosprite.eo.tools.catalog.core.stac.match import match_across_collections

from .common import get_catalog_client, item_to_feature
from .registry import catalog_tool

class CollectionIn(BaseModel):
    name: str
    provider: str | None = None


class SearchMatchIn(BaseModel):
    collections: list[CollectionIn | str] = Field(
        min_length=1,
        description="Collections to search and optionally match.",
    )
    datetime: str = Field(description="Date range such as 2024-01-01/2024-02-01.")
    bbox: str | None = None
    geometry: str | None = None
    tile: str | None = None
    assets: dict[str, list[str]] | None = None
    cloud_cover: str | None = None
    nodata_percent: str | None = None
    orbit_state: str | None = None
    provider: str | None = Field(default=None, description="Global provider fallback.")
    include_collections: bool = False
    max_interval_days: float | None = 3.0
    min_overlap_ratio: float = 0.1
    anchor_collection: str | None = None

    def resolved_collections(self) -> list[CollectionIn]:
        result = []
        for collection in self.collections:
            if isinstance(collection, str):
                result.append(CollectionIn(name=collection, provider=self.provider))
            else:
                result.append(CollectionIn(name=collection.name, provider=collection.provider or self.provider))
        return result


class SearchMatchOut(BaseModel):
    result: dict[str, Any]


@catalog_tool
class SearchMatchTool(Tool[SearchMatchIn, SearchMatchOut]):
    name = "catalog.search_match"
    version = "1.0.0"
    domain = "catalog"
    summary = "Search and optionally match items across STAC collections."
    description = "Query multiple collections, optionally matching scenes by time and spatial overlap."
    InputModel = SearchMatchIn
    OutputModel = SearchMatchOut

    async def run(self, ctx: ToolContext, inputs: SearchMatchIn) -> SearchMatchOut:
        loop = asyncio.get_running_loop()

        async def search_one(collection: CollectionIn) -> tuple[str, list, str | None]:
            query_kwargs = {
                key: value for key, value in {
                    "datetime": inputs.datetime,
                    "bbox": inputs.bbox,
                    "geometry": inputs.geometry,
                    "tile": inputs.tile,
                    "assets": (inputs.assets or {}).get(collection.name),
                    "cloud_cover": inputs.cloud_cover,
                    "nodata_percent": inputs.nodata_percent,
                    "orbit_state": inputs.orbit_state,
                }.items() if value is not None
            }
            try:
                client = get_catalog_client(collection.provider)
                query = client.create_query(collection.name, **query_kwargs)
                items = await loop.run_in_executor(None, lambda: client.search(query))
                return collection.name, items, None
            except Exception as exc:
                return collection.name, [], str(exc)

        search_results = await asyncio.gather(*[search_one(collection) for collection in inputs.resolved_collections()])

        items_by_collection: dict[str, list] = {}
        errors: dict[str, str] = {}
        for collection, items, error in search_results:
            items_by_collection[collection] = items
            if error:
                errors[collection] = error

        summary = {collection: len(items) for collection, items in items_by_collection.items()}
        collections_out = {
            collection: {
                "type": "FeatureCollection",
                "stac_version": "1.0.0",
                "features": [item_to_feature(item, collection).model_dump(mode="json") for item in items],
            }
            for collection, items in items_by_collection.items()
        }

        response: dict[str, Any] = {
            "type": "MultiCollectionMatchResult" if inputs.max_interval_days is not None else "MultiCollectionResult",
            "stac_version": "1.0.0",
            "summary": summary,
        }
        if inputs.max_interval_days is None or inputs.include_collections:
            response["collections"] = collections_out

        if inputs.max_interval_days is not None:
            groups = match_across_collections(
                items_by_collection,
                max_interval_days=inputs.max_interval_days,
                min_overlap_ratio=inputs.min_overlap_ratio,
                anchor_collection=inputs.anchor_collection,
            )
            response["anchor_collection"] = groups[0].anchor_collection if groups else inputs.anchor_collection
            response["match_count"] = len(groups)
            response["matches"] = [
                {
                    "max_time_delta_seconds": group.max_time_delta_seconds,
                    "features": [
                        item_to_feature(item, collection).model_dump(mode="json")
                        for collection, item in group.items.items()
                    ],
                }
                for group in groups
            ]

        if errors:
            response["errors"] = errors
        return SearchMatchOut(result=response)
