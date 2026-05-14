from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool
from .core import RasterItem, compute_common_extent, prepare_items_for_crop


class CropIntersectionItem(BaseModel):
    name: str = Field(description="Logical item name used as the item key in results")
    assets: dict[str, str | dict] = Field(description="Band name to raster path, remote URL, or asset descriptor")
    id: str | None = Field(default=None, description="Original catalog item id")
    collection: str | None = Field(default=None, description="Original catalog collection")
    datetime: str | None = Field(default=None, description="Item acquisition datetime")
    tile: str | None = Field(default=None, description="Spatial tile/path-row token")
    geometry: dict | None = Field(default=None, description="Original catalog item geometry in WGS84")

    def to_model(self) -> RasterItem:
        return RasterItem(
            name=self.name,
            assets=dict(self.assets),
            item_id=self.id,
            collection=self.collection,
            datetime=self.datetime,
            tile=self.tile,
            geometry=self.geometry,
        )


class CropIntersectionIn(BaseModel):
    items: list[CropIntersectionItem]
    anchor_item: str | None = None


class CropIntersectionOut(BaseModel):
    result: dict[str, Any] = Field(description="Computed common extent payload.")


def _items_by_name(items: list[CropIntersectionItem]) -> dict[str, RasterItem]:
    return {item.name: item.to_model() for item in items}


def _extent_payload(extent) -> dict[str, Any]:
    return {
        "anchor_item": extent.anchor_item,
        "crs": extent.crs,
        "bounds": extent.bounds,
        "intersection_wgs84": extent.intersection_wgs84,
    }


@tool
class CropIntersectionTool(BaseRasterTool):
    name = "crop.intersection"
    domain = "raster"
    summary = "Compute common crop extent."
    description = "Computes the common intersection extent for a group of raster items."
    InputModel = CropIntersectionIn
    OutputModel = CropIntersectionOut

    async def run(self, ctx: ToolContext, inputs: CropIntersectionIn) -> CropIntersectionOut:
        ctx.logger.info("raster.crop_intersection item_count=%s", len(inputs.items))
        items = prepare_items_for_crop(_items_by_name(inputs.items))
        extent = compute_common_extent(items, anchor_item=inputs.anchor_item)
        return CropIntersectionOut(result=_extent_payload(extent))
