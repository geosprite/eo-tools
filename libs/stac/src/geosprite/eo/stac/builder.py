"""Helpers for building and serializing STAC payloads."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from .assets import Asset
from .collections import Collection, collection_extent
from .items import Item


def _datetime_text(value: str | datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return value


def build_item_from_assets(
    *,
    item_id: str,
    collection: str,
    assets: dict[str, Asset] | dict[str, dict[str, Any]],
    geometry: dict[str, Any] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    properties: dict[str, Any] | None = None,
    datetime_value: str | datetime | date | None = None,
) -> Item:
    """Build a STAC Item from eo-tools processing/model output assets."""

    item_properties = dict(properties or {})
    datetime_text = _datetime_text(datetime_value)
    if datetime_text is not None and "datetime" not in item_properties:
        item_properties["datetime"] = datetime_text
    return Item(
        stac_version="1.0.0",
        id=item_id,
        collection=collection,
        geometry=geometry,
        bbox=list(bbox) if bbox is not None else None,
        properties=item_properties,
        assets={
            key: value if isinstance(value, Asset) else Asset.model_validate(value)
            for key, value in assets.items()
        },
    )


def build_collection(
    *,
    collection_id: str,
    description: str,
    title: str | None = None,
    license: str = "proprietary",
    spatial_bbox: list[float] | tuple[float, ...] | None = None,
    temporal_interval: list[str | None] | tuple[str | None, str | None] | None = None,
    keywords: list[str] | None = None,
    providers: list[dict[str, Any]] | None = None,
    summaries: dict[str, Any] | None = None,
    item_assets: dict[str, dict[str, Any]] | None = None,
) -> Collection:
    """Build a minimal STAC Collection suitable for transaction APIs."""

    return Collection(
        id=collection_id,
        title=title,
        description=description,
        license=license,
        extent=collection_extent(bbox=spatial_bbox, interval=temporal_interval),
        keywords=keywords,
        providers=providers,
        summaries=summaries,
        item_assets=item_assets,
    )


def asset_to_stac_dict(asset: Asset) -> dict[str, Any]:
    """Serialize an Asset and flatten extra_fields into STAC extension fields."""

    data = asset.model_dump(by_alias=True, exclude_none=True)
    extra = data.pop("extra_fields", None) or {}
    data.update(extra)
    return data


def item_to_stac_dict(item: Item) -> dict[str, Any]:
    """Serialize an Item for STAC APIs."""

    data = item.model_dump(by_alias=True, exclude_none=True)
    data["assets"] = {
        key: asset_to_stac_dict(asset if isinstance(asset, Asset) else Asset.model_validate(asset))
        for key, asset in item.assets.items()
    }
    return data


def collection_to_stac_dict(collection: Collection) -> dict[str, Any]:
    """Serialize a Collection for STAC APIs."""

    data = collection.model_dump(by_alias=True, exclude_none=True)
    if collection.assets is not None:
        data["assets"] = {
            key: asset_to_stac_dict(asset if isinstance(asset, Asset) else Asset.model_validate(asset))
            for key, asset in collection.assets.items()
        }
    return data


__all__ = [
    "asset_to_stac_dict",
    "build_collection",
    "build_item_from_assets",
    "collection_to_stac_dict",
    "item_to_stac_dict",
]
