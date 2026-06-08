# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Raster stack tool."""

from __future__ import annotations

import asyncio

from pydantic import Field

from geosprite.eo.raster import stack_images, stack_rgb_images
from geosprite.eo.store import localize_url_inputs, OperationIn, OperationOut, Output
from geosprite.eo.tools import Tool, ToolContext, tool


class StackRasterIn(OperationIn):
    """Raster stack inputs and output controls."""


class StackRgbRasterIn(OperationIn):
    """RGB raster stack inputs and output controls."""

    output_format: str = Field(
        default="JPEG_COG",
        description="RGB stack output format. Defaults to JPEG-compressed COG for compact visual products.",
    )
    input_files: list[str] = Field(
        min_length=3,
        max_length=3,
        description="Three raster input paths or URIs in red, green, blue order.",
    )


@tool
class StackRasterTool(Tool[StackRasterIn, OperationOut]):
    name = "stack"
    domain = "raster"
    summary = "Stack single-band rasters into a multiband raster."
    description = (
        "Align same-extent single-band raster inputs to the highest-resolution grid, "
        "and stack them into one local output."
    )
    InputModel = StackRasterIn
    OutputModel = OperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: StackRasterIn) -> OperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = Output.from_context(
            ctx.store,
            ctx.workdir,
            inputs.output_file,
            "stack.tif",
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
            lambda: stack_images(
                inputs.input_files,
                str(output.local_path),
                output_format=inputs.output_format,
            ),
        )

        return output.complete(result_path)


@tool
class StackRgbRasterTool(Tool[StackRgbRasterIn, OperationOut]):
    name = "stack_rgb"
    domain = "raster"
    summary = "Stack three single-band rasters into an 8-bit RGB raster."
    description = (
        "Align three same-extent single-band raster inputs in red, green, blue order, "
        "stretch them to 8-bit, and write one local RGB output."
    )
    InputModel = StackRgbRasterIn
    OutputModel = OperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: StackRgbRasterIn) -> OperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = Output.from_context(
            ctx.store,
            ctx.workdir,
            inputs.output_file,
            "rgb.tif",
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
            lambda: stack_rgb_images(
                inputs.input_files,
                str(output.local_path),
                output_format=inputs.output_format,
            ),
        )

        return output.complete(result_path)


__all__ = [
    "StackRasterIn",
    "StackRasterTool",
    "StackRgbRasterIn",
    "StackRgbRasterTool",
]
