# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Raster composition tool."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from geosprite.eo.raster.mosaic import mosaic_images, mosaic_json
from geosprite.eo.store import localize_url_inputs, OperationIn, OperationOut, Output
from geosprite.eo.tools import Tool, ToolContext, tool


@tool
class MosaicRasterTool(Tool[OperationIn, OperationOut]):
    name = "mosaic"
    domain = "raster"
    summary = "Compose aligned single-band rasters by max, min, or median."
    description = (
        "Align same-extent single-band raster inputs to the highest-resolution grid, "
        "and compose valid pixels into one local output."
    )
    InputModel = OperationIn
    OutputModel = OperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: OperationIn) -> OperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = Output.from_context(
            ctx.store,
            ctx.workdir,
            inputs.output_file,
            "mosaic.tif",
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
            lambda: mosaic_images(
                inputs.input_files,
                str(output.local_path),
                output_format=inputs.output_format,
            ),
        )

        return output.complete(result_path)


class RasterMosaicJsonIn(BaseModel):
    output: str
    urls: list[str] | None = None
    text: str | None = None


@tool
class RasterMosaicJsonTool(Tool[OperationIn, OperationOut]):
    name = "mosaic.mosaic_json"
    domain = "raster"
    summary = "Mosaic rasters from JSON/text."
    description = "Extracts raster URLs from a JSON/text payload or uses explicit URLs, then mosaics them."
    InputModel = RasterMosaicJsonIn
    OutputModel = OperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: OperationIn) -> OperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = Output.from_context(
            ctx.store,
            ctx.workdir,
            inputs.output_file,
            "mosaic.tif",
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
            lambda: mosaic_json(
                inputs.output_file,
                inputs.input_files,
            ),
        )

        return output.complete(result_path)


__all__ = ["MosaicRasterTool"]
