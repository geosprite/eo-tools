from __future__ import annotations

from dataclasses import replace

import numpy as np
from pydantic import BaseModel, Field

from geosprite.eo.io.raster import DatasetReader, write_cog
from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext, tool
from geosprite.eo.tools.raster.outputs import local_output_path, publish_output

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from .common import gdt_type

class CompositeMedianIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


def median(input_files: list[str], output_file: str) -> None:
    reader = DatasetReader(*input_files)
    data = reader.read(nodata_to_nan=True)
    data = np.percentile(data, 50, axis=0, method="higher")
    if np.issubdtype(data.dtype, np.floating):
        data = data.astype(np.float32)
    profile = replace(reader.profile, band_count=1, gdal_data_type=gdt_type(data))
    write_cog(data, output_file, profile)


@tool
class CompositeMedianTool(BaseRasterTool):
    name = "compose.median"
    domain = "compose"
    summary = "Calculate median composite."
    InputModel = CompositeMedianIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: CompositeMedianIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("median", inputs.output)
        median(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "median", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
