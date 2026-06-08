# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Raster composition tool."""

from __future__ import annotations

import asyncio

from pydantic import Field

from geosprite.eo.raster.models import RasterOperationIn, RasterOperationOut, RasterOutput
from geosprite.eo.raster import CompositionMethod, compose_images
from geosprite.eo.store import localize_url_inputs
from geosprite.eo.tools import Tool, ToolContext, tool


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

        output = RasterOutput.from_context(
            ctx.store,
            ctx.workdir,
            inputs.output_file,
            f"{inputs.method.value}.tif",
            run_id=ctx.run_id,
            overwrite=inputs.overwrite,
            presign_url=inputs.presign_url,
            presign_expires_in=inputs.presign_expires_in,
        )

        existing = output.existing_result()
        if existing is not None:
            return existing

        output.local_path.parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()

        result_path = await loop.run_in_executor(
            None,
            lambda: compose_images(
                inputs.input_files,
                str(output.local_path),
                method=inputs.method,
                output_format=inputs.output_format,
            ),
        )

        return output.complete(result_path)


__all__ = ["ComposeRasterIn", "ComposeRasterTool"]
