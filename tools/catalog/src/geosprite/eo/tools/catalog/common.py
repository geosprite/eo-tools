from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import BaseModel

from geosprite.eo.stac import Asset, DEFAULT_MEDIA_TYPE, Item, ItemCollection

from .stac import Catalog

class DictResultOut(BaseModel):
    result: dict[str, Any]


def get_catalog_client(provider: str | None = None) -> Catalog:
    return Catalog(provider) if provider else Catalog()


def _asset_from_provider_value(value: Any) -> Asset:
    if isinstance(value, str):
        return Asset(href=value)
    if isinstance(value, dict):
        href = value.get("href") or value.get("uri")
        if isinstance(href, str):
            extra = {key: val for key, val in value.items() if key not in {"href", "uri", "type", "media_type"}}
            return Asset(
                href=href,
                type=value.get("media_type") or value.get("type") or DEFAULT_MEDIA_TYPE,
                extra_fields=extra,
            )
    return Asset(href=str(value), extra_fields={"raw": value})


def item_to_feature(item, collection: str) -> Item:
    d = asdict(item) if is_dataclass(item) else vars(item)

    feature_id = d.get("id")
    assets = d.get("assets") or {}
    geometry = d.get("geometry")
    properties = {
        k: v for k, v in d.items()
        if k not in {"id", "assets", "geometry"}
    }
    if "datetime" in properties and hasattr(properties["datetime"], "isoformat"):
        properties["datetime"] = properties["datetime"].isoformat()
    if "cloud_cover" in properties and "eo:cloud_cover" not in properties:
        properties["eo:cloud_cover"] = properties["cloud_cover"]

    return Item(
        id=str(feature_id),
        collection=collection,
        geometry=geometry,
        properties=properties,
        assets={key: _asset_from_provider_value(value) for key, value in assets.items()},
    )


def execute_search(collection: str, query_kwargs: dict[str, Any], provider: str | None = None) -> ItemCollection:
    client = get_catalog_client(provider)
    query = client.create_query(collection, **query_kwargs)
    results = client.search(query)
    return ItemCollection(
        features=[item_to_feature(item, collection) for item in results],
    )
