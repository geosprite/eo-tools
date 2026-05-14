from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool, raster_asset
from .core import (
    CommonExtent,
    RasterItem,
    crop_item_to_extent,
    crop_output_url,
    output_folder,
    prepare_item_for_crop,
    publish_crop_files,
)


class CropItemPayload(BaseModel):
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


class CropItemExtentPayload(BaseModel):
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


class CropItemToExtentIn(BaseModel):
    item: CropItemPayload
    extent: CropItemExtentPayload
    spatial_key: str
    time_key: str
    resampling: str = "bicubic"


class CropItemToExtentOut(BaseModel):
    result: dict[str, Any] = Field(description="Published crop result payload.")


def _extent_payload(extent: CommonExtent) -> dict[str, Any]:
    return {
        "anchor_item": extent.anchor_item,
        "crs": extent.crs,
        "bounds": extent.bounds,
        "intersection_wgs84": extent.intersection_wgs84,
    }


def _assets(urls: dict[str, str]) -> list[dict[str, Any]]:
    return [
        raster_asset(url, title=band, band=band).model_dump(mode="json")
        for band, url in urls.items()
    ]


@tool
class CropItemToExtentTool(BaseRasterTool):
    name = "crop.extent"
    domain = "raster"
    summary = "Crop one raster item to extent."
    description = "Crops one raster item to a supplied common extent."
    InputModel = CropItemToExtentIn
    OutputModel = CropItemToExtentOut

    async def run(self, ctx: ToolContext, inputs: CropItemToExtentIn) -> CropItemToExtentOut:
        ctx.logger.info("raster.crop_item_to_extent item=%s", inputs.item.name)
        extent = inputs.extent.to_model()
        item = prepare_item_for_crop(inputs.item.to_model())
        local_output_folder = output_folder(inputs.spatial_key, inputs.time_key)
        files = crop_item_to_extent(
            item=item,
            output_folder=local_output_folder,
            extent=extent,
            resampling=inputs.resampling,
        )
        urls_by_item = publish_crop_files({item.name: files}, spatial_key=inputs.spatial_key, time_key=inputs.time_key)
        return CropItemToExtentOut(
            result={
                "spatial_key": inputs.spatial_key,
                "time_key": inputs.time_key,
                "output_folder": crop_output_url(inputs.spatial_key, inputs.time_key),
                "extent": _extent_payload(extent),
                "assets": _assets(urls_by_item[item.name]),
            }
        )
