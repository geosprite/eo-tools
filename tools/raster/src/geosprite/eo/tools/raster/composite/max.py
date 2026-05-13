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

class CompositeMaxIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


def maximum(input_files: list[str], output_file: str) -> None:
    reader = DatasetReader(*input_files)
    data = reader.read()
    data = np.max(data, axis=0)
    if reader.profile.nodata is not None:
        data = np.where(np.isnan(data), reader.profile.nodata, data)
    profile = replace(reader.profile, band_count=1, gdal_data_type=gdt_type(data))
    write_cog(data, output_file, profile)


@tool
class CompositeMaxTool(BaseRasterTool):
    name = "compose.max"
    domain = "compose"
    summary = "Calculate maximum composite."
    InputModel = CompositeMaxIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: CompositeMaxIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("maximum", inputs.output)
        maximum(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "maximum", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
