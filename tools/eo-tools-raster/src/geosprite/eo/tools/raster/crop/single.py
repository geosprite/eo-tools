from __future__ import annotations

from pydantic import BaseModel, Field

from geosprite.eo.io.raster import crop_raster
from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool, raster_asset, resolve_input_url
from ..outputs import local_output_path, publish_output


class RasterCropIn(BaseModel):
    input: str = Field(description="Input raster path or URL.")
    output: str = Field(description="Output path or object key.")
    bounds: tuple[float, float, float, float] = Field(description="Output bounds in target CRS.")
    crs: str = Field(description="Target CRS, for example EPSG:32650.")
    resampling: str = "bicubic"
    x_resolution: float | None = None
    y_resolution: float | None = None


@tool
class RasterCropTool(BaseRasterTool):
    name = "crop"
    domain = "raster"
    summary = "Crop one raster to bounds."
    description = "Crops a raster to target bounds/CRS and publishes the output through eo-eo-store/MinIO."
    InputModel = RasterCropIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: RasterCropIn) -> Asset:
        input_path = await resolve_input_url(inputs.input)
        output_path = local_output_path("crop", inputs.output)
        crop_raster(
            input_path=input_path,
            output_path=output_path,
            bounds=inputs.bounds,
            crs=inputs.crs,
            resampling=inputs.resampling,
            x_resolution=inputs.x_resolution,
            y_resolution=inputs.y_resolution,
        )
        return raster_asset(
            publish_output(output_path, "crop", inputs.output),
            title=inputs.output,
            tool=self.name,
        )
