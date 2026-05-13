"""Small STAC Collection schemas used by eo-tools catalog publishing."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .assets import Asset, asset_to_stac_dict

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
    links: list[dict[str, Any]] = Field(default_factory=list)
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
    "build_collection",
    "Collection",
    "collection_extent",
    "collection_to_stac_dict",
    "Extent",
    "SpatialExtent",
    "TemporalExtent",
]
