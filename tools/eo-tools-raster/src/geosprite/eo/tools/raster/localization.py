# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Raster localization tool."""

from __future__ import annotations

from geosprite.eo.raster.models import RasterLocalizationIn, RasterLocalizationOut
from geosprite.eo.store import localize_url_inputs
from geosprite.eo.tools import Tool, ToolContext, tool


@tool
class LocalizeRasterTool(Tool[RasterLocalizationIn, RasterLocalizationOut]):
    name = "localization"
    domain = "raster"
    summary = "Localize raster input files through eo-store."
    description = (
        "Resolve one or more raster URI inputs with eo-store localization. "
        "When bucket is set, localization may return deterministic s3:// URIs; "
        "otherwise URI inputs are fetched under the tool workspace."
    )
    InputModel = RasterLocalizationIn
    OutputModel = RasterLocalizationOut

    @localize_url_inputs
    async def run(
        self,
        ctx: ToolContext,
        inputs: RasterLocalizationIn,
    ) -> RasterLocalizationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        return RasterLocalizationOut(
            input_files=inputs.input_files,
            publish_catalog=False,
        )


__all__ = ["LocalizeRasterTool"]
