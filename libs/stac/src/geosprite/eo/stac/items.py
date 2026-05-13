"""Small STAC item schemas used by eo-tools catalog and publishing tools.

This module follows pystac naming where it helps readability (`Item`,
`ItemCollection`, `Link`) without depending on pystac or modeling every STAC
field. Only the fields consumed by eo-tools services are included.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .assets import Asset


class Link(BaseModel):
    model_config = ConfigDict(extra="allow")

    rel: str
    href: str
    media_type: str | None = Field(default=None, alias="type")
    title: str | None = None


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
    links: list[Link] | None = None


class ItemCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    stac_version: str = "1.0.0"
    features: list[Item] = Field(default_factory=list)
    links: list[Link] | None = None
    context: dict[str, Any] | None = None


# Backward-compatible names used by existing services.
StacLink = Link
StacFeature = Item
StacFeatureCollection = ItemCollection


__all__ = [
    "Link",
    "Item",
    "ItemCollection",
    "StacLink",
    "StacFeature",
    "StacFeatureCollection",
]
