from __future__ import annotations

from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext
from pydantic import BaseModel, Field

from geosprite.eo.tools.raster.outputs import local_output_path, publish_output

from .core import mosaic
from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from ..registry import raster_tool


class RasterMosaicIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")
    cutline_geojson: str | None = None


@raster_tool
class RasterMosaicTool(BaseRasterTool):
    name = "raster.mosaic"
    domain = "raster"
    summary = "Mosaic rasters."
    description = "Merges multiple raster inputs into a mosaic, optionally with a cutline GeoJSON."
    InputModel = RasterMosaicIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: RasterMosaicIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("mosaic", inputs.output)
        mosaic(input_paths, output_path, inputs.cutline_geojson)
        return raster_asset(
            publish_output(output_path, "mosaic", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
