from __future__ import annotations

from pydantic import BaseModel

from geosprite.eo.stac import Asset
from geosprite.eo.tools import ToolContext, tool
from geosprite.eo.tools.raster.outputs import local_output_path, publish_output

from ..common import BaseRasterTool, extract_urls, raster_asset, resolve_input_urls
from .core import mosaic_json

class RasterMosaicJsonIn(BaseModel):
    output: str
    urls: list[str] | None = None
    text: str | None = None


@tool
class RasterMosaicJsonTool(BaseRasterTool):
    name = "raster.mosaic_json"
    domain = "raster"
    summary = "Mosaic rasters from JSON/text."
    description = "Extracts raster URLs from a JSON/text payload or uses explicit URLs, then mosaics them."
    InputModel = RasterMosaicJsonIn
    OutputModel = Asset

    async def run(self, ctx: ToolContext, inputs: RasterMosaicJsonIn) -> Asset:
        urls = inputs.urls or extract_urls(inputs.text or "")
        urls = await resolve_input_urls(urls)
        output_path = local_output_path("mosaicjson", inputs.output)
        mosaic_json(output_path, urls)
        return raster_asset(
            publish_output(output_path, "mosaicjson", inputs.output),
            title=inputs.output,
            tool=self.name,
            input_count=len(urls),
        )
