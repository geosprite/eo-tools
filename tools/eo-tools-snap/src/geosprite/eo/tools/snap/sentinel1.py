# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Sentinel-1 SNAP preprocessing tool."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse

from pydantic import Field, model_validator

from geosprite.eo.raster.models import RasterOperationIn, RasterOperationOut, RasterOutput
from geosprite.eo.store import localize_url_inputs
from geosprite.eo.tools import Tool, ToolContext, tool

from .core.sentinel1 import preprocess


class SNAPSentinel1In(RasterOperationIn):
    """Sentinel-1 SNAP preprocessing inputs and output controls."""

    manifest_name: ClassVar[str] = "manifest.safe"
    polar_names: ClassVar[list[str]] = [
        "measurement/iw-vv.tiff",
        "measurement/iw-vh.tiff",
    ]
    files: ClassVar[list[str]] = [
        manifest_name,
        "preview/quick-look.png",
        *polar_names,
        "annotation/calibration/noise-iw-vv.xml",
        "annotation/calibration/noise-iw-vh.xml",
        "annotation/calibration/calibration-iw-vv.xml",
        "annotation/calibration/calibration-iw-vh.xml",
        "annotation/iw-vv.xml",
        "annotation/iw-vh.xml",
    ]

    manifest_file: str = Field(
        description="Sentinel-1 manifest.safe path or URI passed to SNAP preprocessing.",
    )
    polar_files: list[str] = Field(
        min_length=2,
        max_length=2,
        description="Sentinel-1 VV and VH measurement file paths or URIs.",
    )

    input_dir: str | None = Field(
        default=None,
        description="Sentinel-1 SAFE input directory used to derive required SNAP sidecar files.",
    )

    @model_validator(mode="before")
    @classmethod
    def _derive_input_files(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        values = dict(data)
        input_dir = data.get("input_dir")
        if input_dir is not None and not values.get("input_files"):
            values["input_files"] = [_join_input_file(input_dir, file) for file in cls.files]
        elif (
            not values.get("input_files")
            and values.get("manifest_file")
            and values.get("polar_files")
        ):
            values["input_files"] = [values["manifest_file"], *values["polar_files"]]

        input_files = values.get("input_files") or []
        if not values.get("manifest_file"):
            values["manifest_file"] = _preprocess_inputs(input_files)[0]
        if not values.get("polar_files"):
            values["polar_files"] = _preprocess_inputs(input_files)[1]

        return values


def _join_input_file(input_dir: str, file: str) -> str:
    parsed = urlparse(input_dir)
    if parsed.scheme and len(parsed.scheme) > 1:
        return f"{input_dir.rstrip('/')}/{file}"

    return str(Path(input_dir) / file)


def _select_input_file(
    input_files: list[str],
    file_name: str,
    fallback_indices: tuple[int, ...],
) -> str:
    normalized_name = file_name.replace("\\", "/").lower()
    for input_file in input_files:
        normalized_file = str(input_file).replace("\\", "/").lower()
        if normalized_file.endswith(normalized_name):
            return str(input_file)

    for fallback_index in fallback_indices:
        try:
            return str(input_files[fallback_index])
        except IndexError:
            continue

    raise ValueError(f"Sentinel-1 input_files must include {file_name!r}.")


def _select_polar_file(
    input_files: list[str],
    polarization: str,
    fallback_indices: tuple[int, ...],
) -> str:
    normalized_polarization = polarization.lower()
    legacy_name = f"measurement/iw-{normalized_polarization}.tiff"

    for input_file in input_files:
        normalized_file = str(input_file).replace("\\", "/").lower()
        if not normalized_file.endswith(".tiff"):
            continue
        if f"/measurement/" not in normalized_file:
            continue
        if normalized_file.endswith(legacy_name) or f"-{normalized_polarization}-" in normalized_file:
            return str(input_file)

    for fallback_index in fallback_indices:
        try:
            return str(input_files[fallback_index])
        except IndexError:
            continue

    raise ValueError(f"Sentinel-1 input_files must include a {polarization.upper()} measurement.")


def _preprocess_inputs(input_files: list[str]) -> tuple[str, list[str]]:
    manifest_file = _select_input_file(input_files, SNAPSentinel1In.manifest_name, (0,))
    polar_files = [
        _select_polar_file(input_files, polarization, fallback_indices)
        for fallback_indices, polarization in (
            ((2, 1), "vv"),
            ((3, 2), "vh"),
        )
    ]
    return manifest_file, polar_files


def _preprocess_polarizations(polar_files: list[str]) -> list[str]:
    polarizations = []
    for polar_file in polar_files:
        normalized_file = str(polar_file).replace("\\", "/").lower()
        for polarization in ("vv", "vh", "hh", "hv"):
            if (
                normalized_file.endswith(f"iw-{polarization}.tiff")
                or f"-{polarization}-" in normalized_file
            ):
                polarizations.append(polarization.upper())
                break
        else:
            raise ValueError(f"Cannot determine Sentinel-1 polarization from {polar_file!r}.")
    return polarizations


@tool
class SNAPSentinel1Tool(Tool[SNAPSentinel1In, RasterOperationOut]):
    name = "sentinel1"
    domain = "snap"
    summary = "Preprocess Sentinel-1 GRD with ESA SNAP."
    description = (
        "Run Sentinel-1 SNAP preprocessing from a SAFE directory or explicit SAFE sidecar files."
    )
    InputModel = SNAPSentinel1In
    OutputModel = RasterOperationOut

    @localize_url_inputs
    async def run(self, ctx: ToolContext, inputs: SNAPSentinel1In) -> RasterOperationOut:
        if inputs.publish_catalog:
            raise NotImplementedError("Catalog publication is deferred for raster tools.")

        output = RasterOutput.from_context(
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
            lambda: _run_preprocess(inputs.input_files, ctx.workdir),
        )

        return output.complete(result_path)


def _run_preprocess(input_files: list[str], workdir: Path):
    manifest_file, polar_files = _preprocess_inputs(input_files)
    return preprocess(
        manifest_file,
        _preprocess_polarizations(polar_files),
        workdir,
    )


__all__ = [
    "SNAPSentinel1In",
    "SNAPSentinel1Tool",
]
