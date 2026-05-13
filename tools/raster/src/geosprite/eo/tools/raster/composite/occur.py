from __future__ import annotations

from dataclasses import replace

import numpy as np
from pydantic import BaseModel, Field

from geosprite.eo.io.raster import DatasetReader, write_cog
from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext
from geosprite.eo.tools.raster.outputs import local_output_path, publish_output

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from .common import gdt_type
from ..registry import raster_tool

class CompositeOccurIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


def occur(input_files: list[str], output_file: str) -> None:
    reader = DatasetReader(*input_files)
    data = reader.read()
    non_zero_mask = data != 0
    non_zero_count = np.sum(non_zero_mask, axis=0)
    occur_ratio = (non_zero_count / data.shape[0]).astype(np.float32)
    nodata = -1
    occur_ratio = np.where(np.isnan(occur_ratio), nodata, occur_ratio)
    profile = replace(reader.profile, band_count=1, gdal_data_type=gdt_type(occur_ratio), nodata=nodata)
    write_cog(occur_ratio, output_file, profile)


@raster_tool
class CompositeOccurTool(BaseRasterTool):
    name = "compose.occur"
    domain = "compose"
    summary = "Calculate raster occurrence."
    InputModel = CompositeOccurIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: CompositeOccurIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("occur", inputs.output)
        occur(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "occur", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
