from __future__ import annotations

from pydantic import BaseModel, Field

from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext
from geosprite.eo.tools.raster.outputs import local_output_path, publish_output

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from .core import stack_images
from ..registry import raster_tool

class RasterStackIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


@raster_tool
class RasterStackTool(BaseRasterTool):
    name = "raster.stack"
    domain = "raster"
    summary = "Stack rasters into bands."
    description = "Stacks multiple input rasters into one multi-band raster."
    InputModel = RasterStackIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: RasterStackIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("stack", inputs.output)
        stack_images(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "stack", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
