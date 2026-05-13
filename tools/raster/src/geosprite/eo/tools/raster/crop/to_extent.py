from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool, raster_asset
from .core import (
    CommonExtent,
    RasterItem,
    crop_group_to_extent,
    crop_output_url,
    output_folder,
    prepare_items_for_crop,
    publish_crop_files,
)

class CropToExtentItem(BaseModel):
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


class CropToExtentExtent(BaseModel):
    anchor_item: str
    crs: str
    bounds: tuple[float, float, float, float]
    intersection_wgs84: dict | None = None

    def to_model(self) -> CommonExtent:
        return CommonExtent(
            anchor_item=self.anchor_item,
            crs=self.crs,
            bounds=tuple(self.bounds),
            intersection_wgs84=self.intersection_wgs84 or {"type": "Polygon", "coordinates": []},
        )


class CropToExtentIn(BaseModel):
    items: list[CropToExtentItem]
    extent: CropToExtentExtent
    spatial_key: str
    time_key: str
    resampling: str = "bicubic"


class CropToExtentOut(BaseModel):
    result: dict[str, Any] = Field(description="Published crop result payload.")


def _items_by_name(items: list[CropToExtentItem]) -> dict[str, RasterItem]:
    return {item.name: item.to_model() for item in items}


def _extent_payload(extent: CommonExtent) -> dict[str, Any]:
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


@tool
class CropToExtentTool(BaseRasterTool):
    name = "raster.crop_to_extent"
    domain = "raster"
    summary = "Crop raster group to extent."
    description = "Crops every item in a raster group to a supplied common extent."
    InputModel = CropToExtentIn
    OutputModel = CropToExtentOut

    async def run(self, ctx: ToolContext, inputs: CropToExtentIn) -> CropToExtentOut:
        ctx.logger.info("raster.crop_to_extent item_count=%s", len(inputs.items))
        extent = inputs.extent.to_model()
        items = prepare_items_for_crop(_items_by_name(inputs.items))
        local_output_folder = output_folder(inputs.spatial_key, inputs.time_key)
        files_by_item = crop_group_to_extent(
            items_by_name=items,
            output_folder=local_output_folder,
            extent=extent,
            resampling=inputs.resampling,
        )
        urls_by_item = publish_crop_files(files_by_item, spatial_key=inputs.spatial_key, time_key=inputs.time_key)
        return CropToExtentOut(
            result={
                "spatial_key": inputs.spatial_key,
                "time_key": inputs.time_key,
                "output_folder": crop_output_url(inputs.spatial_key, inputs.time_key),
                "extent": _extent_payload(extent),
                "assets_by_item": _assets_by_item(urls_by_item),
            }
        )
