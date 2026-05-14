from __future__ import annotations

from pydantic import BaseModel, Field

from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from ..outputs import local_output_path, publish_output
from .core import mosaic


class RasterMosaicIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")
    cutline_geojson: str | None = None


@tool
class RasterMosaicTool(BaseRasterTool):
    name = "mosaic"
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
