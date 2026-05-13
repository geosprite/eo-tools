from __future__ import annotations

from dataclasses import replace

import numpy as np

from geosprite.eo.stac import Asset
from geosprite.eo.tools.raster.outputs import local_output_path, publish_output
from geosprite.eo.io.raster import DatasetReader, write_cog
from geosprite.eo.tools import ToolContext
from pydantic import BaseModel, Field

from .common import gdt_type
from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from ..registry import raster_tool


class CompositeMinIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


def minimum(input_files: list[str], output_file: str) -> None:
    reader = DatasetReader(*input_files)
    data = reader.read(nodata_to_nan=True)
    data = np.min(data, axis=0)
    if reader.profile.nodata is not None:
        data = np.where(np.isnan(data), reader.profile.nodata, data)
    profile = replace(reader.profile, band_count=1, gdal_data_type=gdt_type(data))
    write_cog(data, output_file, profile)


@raster_tool
class CompositeMinTool(BaseRasterTool):
    name = "compose.min"
    domain = "compose"
    summary = "Calculate minimum composite."
    InputModel = CompositeMinIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: CompositeMinIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("minimum", inputs.output)
        minimum(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "minimum", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
