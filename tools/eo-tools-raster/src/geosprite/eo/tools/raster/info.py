from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geosprite.eo.store import localize_url_inputs, OperationIn
from geosprite.eo.tools import Tool, ToolContext, tool


class RasterInfoIn(BaseModel):
    input: str = Field(description="Local path, HTTP URL, S3 URL, or GDAL VSI path.")


class RasterInfoOut(BaseModel):
    result: dict[str, Any] = Field(description="Raster metadata returned by GDAL.")


@tool
class RasterInfoTool(Tool[OperationIn, RasterInfoOut]):
    name = "info"
    domain = "raster"
    summary = ""
    description = (
        ""
    )
    InputModel = OperationIn
    OutputModel = RasterInfoOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: OperationIn) -> RasterInfoOut:
        raise NotImplementedError
