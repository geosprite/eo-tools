from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import ToolContext

from ..common import BaseRasterTool, raster_asset
from .core import (
    RasterItem,
    crop_group_to_intersection,
    crop_output_url,
    output_folder,
    prepare_items_for_crop,
    publish_crop_files,
)
from ..registry import raster_tool

class CropToIntersectionItem(BaseModel):
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


class CropToIntersectionIn(BaseModel):
    items: list[CropToIntersectionItem]
    spatial_key: str
    time_key: str
    anchor_item: str | None = None
    resampling: str = "bicubic"


class CropToIntersectionOut(BaseModel):
    result: dict[str, Any] = Field(description="Published crop-to-intersection result payload.")


def _items_by_name(items: list[CropToIntersectionItem]) -> dict[str, RasterItem]:
    return {item.name: item.to_model() for item in items}


def _extent_payload(extent) -> dict[str, Any]:
    return {
        "anchor_item": extent.anchor_item,
        "crs": extent.crs,
        "bounds": extent.bounds,
        "intersection_wgs84": extent.intersection_wgs84,
    }


def _assets_by_item(urls_by_item: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {
        item_name: [
            raster_asset(url, title=band, band=band).model_dump(mode="json")
            for band, url in urls.items()
        ]
        for item_name, urls in urls_by_item.items()
    }


def _run_crop_to_intersection(inputs: CropToIntersectionIn) -> dict[str, Any]:
    items = prepare_items_for_crop(_items_by_name(inputs.items))
    local_output_folder = output_folder(inputs.spatial_key, inputs.time_key)
    result = crop_group_to_intersection(
        items_by_name=items,
        output_folder=local_output_folder,
        spatial_key=inputs.spatial_key,
        time_key=inputs.time_key,
        anchor_item=inputs.anchor_item,
        resampling=inputs.resampling,
    )
    urls_by_item = publish_crop_files(result.files_by_item, spatial_key=result.spatial_key, time_key=result.time_key)
    return {
        "spatial_key": result.spatial_key,
        "time_key": result.time_key,
        "output_folder": crop_output_url(result.spatial_key, result.time_key),
        "extent": _extent_payload(result.extent),
        "assets_by_item": _assets_by_item(urls_by_item),
    }


@raster_tool
class CropToIntersectionTool(BaseRasterTool):
    name = "raster.crop_to_intersection"
    domain = "raster"
    summary = "Crop raster group to intersection."
    description = "Computes the common intersection for a raster group and crops all items to it."
    InputModel = CropToIntersectionIn
    OutputModel = CropToIntersectionOut

    async def run(self, ctx: ToolContext, inputs: CropToIntersectionIn) -> CropToIntersectionOut:
        ctx.logger.info("raster.crop_to_intersection item_count=%s", len(inputs.items))
        return CropToIntersectionOut(result=_run_crop_to_intersection(inputs))
