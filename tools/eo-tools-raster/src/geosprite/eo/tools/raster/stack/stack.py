from __future__ import annotations

from dataclasses import replace
from pydantic import BaseModel, Field

from osgeo import gdal

from geosprite.eo.catalog import Asset
from geosprite.eo.tools import ToolContext, tool
from geosprite.eo.io.raster import DatasetReader, write_cog

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from ..outputs import local_output_path, publish_output


def stack_images(input_files: list[str], output_file: str):
    reader = DatasetReader(*input_files)
    data = reader.read()

    profile = replace(reader.profile, band_count=data.shape[-3] if len(data.shape) > 2 else 1)

    write_cog(data, output_file, profile)


def stack_images2rgb(input_files: list[str], output_file: str):
    reader = DatasetReader(*input_files)
    data = reader.read_as_8bit(2, 98)

    if data.shape[0] < 3:
        raise RuntimeError("The number of data after reading input files should be at least 3")

    profile = replace(reader.profile, band_count=data.shape[0], gdal_data_type=gdal.GDT_Byte, nodata=None)

    write_cog(data, output_file, profile, gci_rgb=True)


class RasterStackIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


@tool
class RasterStackTool(BaseRasterTool):
    name = "stack"
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


@tool
class RasterStackRgbTool(BaseRasterTool):
    name = "stack.rgb"
    domain = "raster"
    summary = "Stack rasters into RGB."
    description = "Stacks three input rasters into one RGB raster."
    InputModel = RasterStackIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: RasterStackIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("stack-rgb", inputs.output)
        stack_images2rgb(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "stack-rgb", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
