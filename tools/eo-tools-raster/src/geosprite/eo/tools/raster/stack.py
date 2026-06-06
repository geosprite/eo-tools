"""Raster stack tool."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import Field

from geosprite.eo.raster import stack_images, stack_rgb_images
from geosprite.eo.store import localize_files
from geosprite.eo.tools import Tool, ToolContext, tool

from .models import RasterOperationIn, RasterOperationOut, local_output_path


class StackRasterIn(RasterOperationIn):
    """Raster stack inputs and output controls."""


class StackRgbRasterIn(RasterOperationIn):
    """RGB raster stack inputs and output controls."""

    input_files: list[str] = Field(
        min_length=3,
        max_length=3,
        description="Three raster input paths or URIs in red, green, blue order.",
    )


@tool
class StackRasterTool(Tool[StackRasterIn, RasterOperationOut]):
    name = "stack"
    domain = "raster"
    summary = "Stack single-band rasters into a multiband raster."
    description = (
        "Align same-extent single-band raster inputs to the highest-resolution grid, "
        "and stack them into one local output."
    )
    InputModel = StackRasterIn
    OutputModel = RasterOperationOut

    @localize_files(preserve_path_structure=True)
    async def run(self, ctx: ToolContext, inputs: StackRasterIn) -> RasterOperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = local_output_path(ctx.workdir, inputs.output_file, "stack.tif")
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
            lambda: stack_images(inputs.input_files, str(output)),
        )
        return RasterOperationOut(
            local_path=str(Path(result_path)),
            destination_uri=None,
            presigned_url=None,
            write_back=True,
            publish_catalog=False,
        )


@tool
class StackRgbRasterTool(Tool[StackRgbRasterIn, RasterOperationOut]):
    name = "stack_rgb"
    domain = "raster"
    summary = "Stack three single-band rasters into an 8-bit RGB raster."
    description = (
        "Align three same-extent single-band raster inputs in red, green, blue order, "
        "stretch them to 8-bit, and write one local RGB output."
    )
    InputModel = StackRgbRasterIn
    OutputModel = RasterOperationOut

    @localize_files(preserve_path_structure=True)
    async def run(self, ctx: ToolContext, inputs: StackRgbRasterIn) -> RasterOperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = local_output_path(ctx.workdir, inputs.output_file, "rgb.tif")
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
            lambda: stack_rgb_images(
                inputs.input_files,
                str(output)
            ),
        )
        return RasterOperationOut(
            local_path=str(Path(result_path)),
            destination_uri=None,
            presigned_url=None,
            write_back=True,
            publish_catalog=False,
        )


__all__ = [
    "StackRasterIn",
    "StackRasterTool",
    "StackRgbRasterIn",
    "StackRgbRasterTool",
]
