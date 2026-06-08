# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Raster localization tool."""

from __future__ import annotations

from geosprite.eo.store import localize_url_inputs, LocalizationIn, LocalizationOut
from geosprite.eo.tools import Tool, ToolContext, tool


@tool
class LocalizeRasterTool(Tool[LocalizationIn, LocalizationOut]):
    name = "localization"
    domain = "raster"
    summary = "Localize raster input files through eo-store."
    description = (
        "Resolve one or more raster URI inputs with eo-store localization. "
        "When bucket is set, localization may return deterministic s3:// URIs; "
        "otherwise URI inputs are fetched under the tool workspace."
    )
    InputModel = LocalizationIn
    OutputModel = LocalizationOut

    @localize_url_inputs
    async def run(
        self,
        ctx: ToolContext,
        inputs: LocalizationIn,
    ) -> LocalizationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        return LocalizationOut(
            input_files=inputs.input_files,
            publish_catalog=False,
        )


__all__ = ["LocalizeRasterTool"]
