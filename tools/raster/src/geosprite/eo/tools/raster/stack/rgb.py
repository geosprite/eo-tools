from __future__ import annotations

from pydantic import BaseModel, Field

from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext, tool
from geosprite.eo.tools.raster.outputs import local_output_path, publish_output

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from .core import stack_images2rgb

class RasterStackRgbIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


@tool
class RasterStackRgbTool(BaseRasterTool):
    name = "raster.stack_rgb"
    domain = "raster"
    summary = "Stack rasters into RGB."
    description = "Stacks three input rasters into one RGB raster."
    InputModel = RasterStackRgbIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: RasterStackRgbIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("stack-rgb", inputs.output)
        stack_images2rgb(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "stack-rgb", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
