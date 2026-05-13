"""Small STAC Collection schemas used by eo-tools catalog publishing."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .assets import Asset
from .items import Link


class SpatialExtent(BaseModel):
    model_config = ConfigDict(extra="allow")

    bbox: list[list[float]]


class TemporalExtent(BaseModel):
    model_config = ConfigDict(extra="allow")

    interval: list[list[str | None]]


class Extent(BaseModel):
    model_config = ConfigDict(extra="allow")

    spatial: SpatialExtent
    temporal: TemporalExtent


class Collection(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["Collection"] = "Collection"
    stac_version: str = "1.0.0"
    id: str
    description: str
    license: str = "proprietary"
    extent: Extent
    links: list[Link] = Field(default_factory=list)
    title: str | None = None
    keywords: list[str] | None = None
    providers: list[dict[str, Any]] | None = None
    summaries: dict[str, Any] | None = None
    assets: dict[str, Asset] | None = None
    item_assets: dict[str, dict[str, Any]] | None = None


def collection_extent(
    *,
    bbox: list[float] | tuple[float, ...] | None = None,
    interval: list[str | None] | tuple[str | None, str | None] | None = None,
) -> Extent:
    """Build a minimal STAC extent."""

    return Extent(
        spatial=SpatialExtent(bbox=[list(bbox or [-180.0, -90.0, 180.0, 90.0])]),
        temporal=TemporalExtent(interval=[list(interval or [None, None])]),
    )


__all__ = ["Collection", "Extent", "SpatialExtent", "TemporalExtent", "collection_extent"]
