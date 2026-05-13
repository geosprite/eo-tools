"""Small STAC item schemas used by eo-tools catalog and publishing tools.

This module follows pystac naming where it helps readability (`Item`,
`ItemCollection`) without depending on pystac or modeling every STAC field.
Only the fields consumed by eo-tools services are included.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .assets import Asset, asset_to_stac_dict

class Item(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["Feature"] = "Feature"
    stac_version: str | None = None
    id: str
    collection: str | None = None
    geometry: dict[str, Any] | None = None
    bbox: list[float] | tuple[float, ...] | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, Asset] = Field(default_factory=dict)
    links: list[dict[str, Any]] | None = None


class ItemCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    stac_version: str = "1.0.0"
    features: list[Item] = Field(default_factory=list)
    links: list[dict[str, Any]] | None = None
    context: dict[str, Any] | None = None


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


def item_to_stac_dict(item: Item) -> dict[str, Any]:
    """Serialize an Item for STAC APIs."""

    data = item.model_dump(by_alias=True, exclude_none=True)
    data["assets"] = {
        key: asset_to_stac_dict(asset if isinstance(asset, Asset) else Asset.model_validate(asset))
        for key, asset in item.assets.items()
    }
    return data


__all__ = [
    "build_item_from_assets",
    "Item",
    "ItemCollection",
    "item_to_stac_dict",
]
