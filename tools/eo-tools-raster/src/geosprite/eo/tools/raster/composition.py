"""Raster composition tool."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import Field

from geosprite.eo.raster import CompositionMethod, compose_images
from geosprite.eo.store import localize_url_inputs
from geosprite.eo.tools import Tool, ToolContext, tool

from .models import RasterOperationIn, RasterOperationOut, local_output_path


class ComposeRasterIn(RasterOperationIn):
    """Raster composition inputs and output controls."""

    method: CompositionMethod = Field(
        default=CompositionMethod.MEDIAN,
        description="Pixel-wise composition method.",
    )


@tool
class ComposeRasterTool(Tool[ComposeRasterIn, RasterOperationOut]):
    name = "compose"
    domain = "raster"
    summary = "Compose aligned single-band rasters by max, min, or median."
    description = (
        "Align same-extent single-band raster inputs to the highest-resolution grid, "
        "and compose valid pixels into one local output."
    )
    InputModel = ComposeRasterIn
    OutputModel = RasterOperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: ComposeRasterIn) -> RasterOperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = local_output_path(ctx.workdir, inputs.output_file, f"{inputs.method.value}.tif")
        if not inputs.overwrite and output.is_file():
            return RasterOperationOut(
                local_path=str(output),
                destination_uri=None,
                presigned_url=None,
                write_back=False,
                publish_catalog=False,
            )

        loop = asyncio.get_running_loop()
        result_path = await loop.run_in_executor(
            None,
            lambda: compose_images(inputs.input_files, str(output), method=inputs.method),
        )

        return RasterOperationOut(
            local_path=str(Path(result_path)),
            destination_uri=None,
            presigned_url=None,
            write_back=True,
            publish_catalog=False,
        )


__all__ = ["ComposeRasterIn", "ComposeRasterTool"]
