from __future__ import annotations

from dataclasses import replace

from pydantic import BaseModel, Field

from geosprite.eo.io.raster import DatasetReader, write_cog
from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool, raster_asset, resolve_input_urls
from ..outputs import local_output_path, publish_output


class CompositeAccumIn(BaseModel):
    inputs: list[str] = Field(description="Input raster paths or URLs.")
    output: str = Field(description="Output path or object key.")


def accum(input_files: list[str], output_file: str) -> None:
    reader = DatasetReader(*input_files)
    data = reader.read()
    data = data.sum()
    profile = replace(reader.profile, band_count=1)
    write_cog(data, output_file, profile)


@tool
class CompositeAccumTool(BaseRasterTool):
    name = "compose.accum"
    domain = "raster"
    summary = "Calculate accumulated composite."
    InputModel = CompositeAccumIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: CompositeAccumIn) -> Asset:
        input_paths = await resolve_input_urls(inputs.inputs)
        output_path = local_output_path("accum", inputs.output)
        accum(input_paths, output_path)
        return raster_asset(
            publish_output(output_path, "accum", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(inputs.inputs),
        )
