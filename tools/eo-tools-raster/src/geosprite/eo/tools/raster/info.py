from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.io.raster import raster_info
from geosprite.eo.tools import ToolContext, tool

from .common import BaseRasterTool


class RasterInfoIn(BaseModel):
    input: str = Field(description="Local path, HTTP URL, S3 URL, or GDAL VSI path.")


class RasterInfoOut(BaseModel):
    result: dict[str, Any] = Field(description="Raster metadata returned by GDAL.")


@tool
class RasterInfoTool(BaseRasterTool):
    name = "info"
    domain = "raster"
    summary = "Read raster metadata."
    description = "Returns GDAL-backed metadata for a raster path, URL, or VSI URI."
    InputModel = RasterInfoIn
    OutputModel = RasterInfoOut

    async def run(self, ctx: ToolContext, inputs: RasterInfoIn) -> RasterInfoOut:
        ctx.logger.info("raster.info input=%s", inputs.input)
        return RasterInfoOut(result=raster_info(inputs.input).as_dict())
