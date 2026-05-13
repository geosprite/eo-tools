from __future__ import annotations

from typing import Any

from geosprite.eo.stac import Asset, AssetCollection
from geosprite.eo.tools import Tool, ToolContext
from pydantic import BaseModel, Field

from ..registry import snap_tool


class Sentinel1SnapIn(BaseModel):
    inputs: list[str] = Field(
        description=(
            "One Sentinel-1 scene base URL or manifest.safe URL. "
            "The service downloads the SAFE sidecar files and runs ESA SNAP preprocessing."
        )
    )


class Sentinel1SnapOut(BaseModel):
    assets: AssetCollection = Field(description="Preprocessed VV/VH GeoTIFF assets.")


def _assets_from_result(result: list[str] | dict[str, Any] | Any) -> AssetCollection:
    if isinstance(result, list):
        urls = [str(item) for item in result]
    elif isinstance(result, dict):
        values = result.get("outputs") or result.get("urls") or result.get("result") or []
        urls = [str(item) for item in values] if isinstance(values, list) else []
    else:
        urls = []

    return AssetCollection(
        items=[
            Asset(
                href=url,
                title=url.rsplit("/", 1)[-1] or None,
                roles=["data"],
                extra_fields={"tool": "preprocess.sentinel1_snap"},
            )
            for url in urls
        ],
        metadata={"tool": "preprocess.sentinel1_snap"},
    )


@snap_tool
class Sentinel1SnapPreprocessTool(Tool[Sentinel1SnapIn, Sentinel1SnapOut]):
    name = "preprocess.sentinel1_snap"
    version = "1.0.0"
    domain = "preprocess"
    summary = "Preprocess Sentinel-1 GRD with ESA SNAP."
    description = (
        "Runs the existing earth-snap Sentinel-1 preprocessing pipeline: download SAFE assets, "
        "thermal noise removal, orbit correction, calibration and terrain correction."
    )
    requires = ["java", "snap", "large_mem"]
    InputModel = Sentinel1SnapIn
    OutputModel = Sentinel1SnapOut

    async def run(self, ctx: ToolContext, inputs: Sentinel1SnapIn) -> Sentinel1SnapOut:
        from geosprite.eo.tools.snap.sentinel1.preprocessing import preprocess_sentinel1

        ctx.logger.info("preprocess.sentinel1_snap input_count=%s", len(inputs.inputs))
        response = await preprocess_sentinel1(inputs=inputs.inputs)
        if isinstance(response, dict) and "result" in response:
            return Sentinel1SnapOut(assets=_assets_from_result(response["result"]))
        return Sentinel1SnapOut(assets=_assets_from_result(response or {}))
