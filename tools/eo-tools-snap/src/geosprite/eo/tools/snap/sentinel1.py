# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Sentinel-1 SNAP preprocessing tool."""

from __future__ import annotations

import asyncio
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar
from urllib.parse import urlparse, urlunparse

from pydantic import Field, model_validator

from geosprite.eo.store import localize_url_inputs, OperationIn, OperationOut, Output
from geosprite.eo.tools import Tool, ToolContext, tool

from .core.sentinel1 import preprocess


class SNAPSentinel1In(OperationIn):
    """Sentinel-1 SNAP preprocessing inputs and output controls."""

    files: ClassVar[list[str]] = [
        "manifest.safe",
        "measurement/iw-vv.tiff",
        "measurement/iw-vh.tiff",
        "annotation/calibration/noise-iw-vv.xml",
        "annotation/calibration/noise-iw-vh.xml",
        "annotation/calibration/calibration-iw-vv.xml",
        "annotation/calibration/calibration-iw-vh.xml",
        "annotation/iw-vv.xml",
        "annotation/iw-vh.xml",
    ]

    input_files: list[str] = Field(
        default_factory=list,
        min_length=9,
        description="Sentinel-1 SAFE files derived from manifest_file unless explicitly provided.",
    )
    manifest_file: str = Field(
        description="Sentinel-1 manifest.safe path or URI passed to SNAP preprocessing.",
    )

    @model_validator(mode="before")
    @classmethod
    def _derive_input_files(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        values = dict(data)

        manifest_file = values.get("manifest_file")
        if manifest_file and not values.get("input_files"):
            manifest_dir = _manifest_base_dir(manifest_file)
            values["input_files"] = [_join_input_file(manifest_dir, file) for file in cls.files]

        return values


def _manifest_base_dir(manifest_file: str) -> str:
    parsed = urlparse(manifest_file)
    if parsed.scheme and len(parsed.scheme) > 1:
        parent_path = PurePosixPath(parsed.path).parent.as_posix()
        if parent_path == ".":
            parent_path = ""
        return urlunparse(parsed._replace(path=parent_path, params="", query="", fragment=""))

    return str(Path(manifest_file).parent)


def _join_input_file(base_dir: str, file: str) -> str:
    parsed = urlparse(base_dir)
    if parsed.scheme and len(parsed.scheme) > 1:
        return f"{base_dir.rstrip('/')}/{file}"

    return str(Path(base_dir) / file)


@tool
class SNAPSentinel1Tool(Tool[SNAPSentinel1In, OperationOut]):
    name = "sentinel1"
    domain = "snap"
    summary = "Preprocess Sentinel-1 GRD with ESA SNAP."
    description = (
        "Run Sentinel-1 SNAP preprocessing from a Sentinel-1 manifest.safe path or URI."
    )
    InputModel = SNAPSentinel1In
    OutputModel = OperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: SNAPSentinel1In) -> OperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = Output.from_context(
            ctx.store,
            ctx.workdir,
            inputs.output_file,
            "sentinel1.tif",
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
            lambda: preprocess(
                inputs.manifest_file,
                ["VV", "VH"],
                str(output.local_path.parent),
            ),
        )

        return output.complete(result_path)


__all__ = [
    "SNAPSentinel1In",
    "SNAPSentinel1Tool",
]
