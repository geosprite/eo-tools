# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

"""Shared raster tool input and output models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from geosprite.eo.tools import ToolContext


class RasterOperationIn(BaseModel):
    """Shared local IO controls for raster tools."""

    model_config = ConfigDict(extra="forbid")

    input_files: list[str] = Field(
        min_length=1,
        description="Raster input paths or URIs passed directly to eo-raster.",
    )
    bucket: str | None = Field(
        default=None,
        description=(
            "Optional S3 bucket used to localize remote input_files before processing. "
            "When set, operators receive localized s3:// URIs; when omitted, URI "
            "inputs are fetched to the runtime workspace."
        ),
    )
    prefix: str | None = Field(
        default=None,
        description="S3 object key prefix used with bucket during input localization.",
    )
    output_file: str | None = Field(
        default=None,
        description=(
            "Raster output target. Local paths write locally; s3:// outputs are "
            "staged locally and uploaded through the ToolContext Store."
        ),
    )
    output_format: str = Field(
        default="COG",
        description=(
            "GDAL output format passed to eo-raster. Use COG for DEFLATE COG, "
            "GTiff for regular GeoTIFF, or JPEG_COG for JPEG-compressed COG."
        ),
    )
    overwrite: bool = Field(
        default=False,
        description="Whether to regenerate and replace an existing local output.",
    )
    publish_catalog: bool = Field(
        default=False,
        description="Explicit future Catalog publication control. Raster tools currently reject true.",
    )
    presign_url: bool = Field(
        default=False,
        description="Whether to return a temporary URL for s3:// outputs.",
    )
    presign_expires_in: int = Field(
        default=3600,
        ge=1,
        description="Temporary URL expiry in seconds when presign_url is true.",
    )

    @model_validator(mode="after")
    def _validate_output_policy(self) -> "RasterOperationIn":
        if self.presign_url and not _is_s3_output(self.output_file):
            raise ValueError("presign_url requires an s3:// output_file.")
        return self


class RasterOperationOut(BaseModel):
    """Normalized raster tool result."""

    local_path: str | None = Field(
        default=None,
        description="Local raster output path.",
    )
    destination_uri: str | None = Field(
        default=None,
        description="Remote output URI when the result was uploaded through Store.",
    )
    presigned_url: str | None = Field(
        default=None,
        description="Temporary URL for a remote output when requested.",
    )
    write_back: bool = Field(description="Whether this request wrote a new output.")
    publish_catalog: bool = Field(description="Whether Catalog publication ran.")


@dataclass(frozen=True)
class RasterOutput:
    """Resolved output target plus Store write/presign policy."""

    store: Any
    local_path: Path
    destination_uri: str | None = None
    overwrite: bool = False
    presign_url: bool = False
    presign_expires_in: int = 3600

    @property
    def is_remote(self) -> bool:
        return self.destination_uri is not None

    @classmethod
    def from_context(
        cls,
        ctx: ToolContext,
        output_file: str | None,
        fallback: str,
        *,
        run_id: str | None = None,
        overwrite: bool = False,
        presign_url: bool = False,
        presign_expires_in: int = 3600,
    ) -> "RasterOutput":
        """Resolve an output target and bind write/presign policy."""

        def _s3_key_parts(path: str) -> tuple[str, ...]:
            key = path.lstrip("/")
            if not key:
                key = fallback
            elif key.endswith("/"):
                key = f"{key}{fallback}"

            parts: list[str] = []
            for part in PurePosixPath(key).parts:
                if part in ("", "."):
                    continue
                if part == ".." or "\\" in part:
                    raise ValueError("s3:// output_file key contains an unsafe path segment.")
                parts.append(part)

            return tuple(parts or (fallback,))

        local_path: Path
        destination_uri: str | None = None

        if _is_s3_output(output_file):
            parsed = urlparse(output_file or "")
            if not parsed.netloc:
                raise ValueError("s3:// output_file must include a bucket name.")

            key_parts = _s3_key_parts(parsed.path)
            run_part = run_id or uuid4().hex

            local_path = ctx.workdir / "raster" / run_part / "outputs" / parsed.netloc

            for key_part in key_parts:
                local_path /= key_part

            destination_uri = f"s3://{parsed.netloc}/{PurePosixPath(*key_parts).as_posix()}"

        elif output_file is not None:
            _path = Path(output_file)
            local_path = _path if _path.is_absolute() else ctx.workdir / _path
        else:
            local_path = ctx.workdir / "raster" / uuid4().hex / fallback

        return cls(
            store=ctx.store,
            local_path=local_path,
            destination_uri=destination_uri,
            overwrite=overwrite,
            presign_url=presign_url,
            presign_expires_in=presign_expires_in,
        )

    def existing_result(self) -> RasterOperationOut | None:
        """Return a skip result when the requested output already exists."""

        if self.is_remote:
            destination_uri = self.destination_uri or ""
            store = self._require_store(destination_uri)

            if not self.overwrite and store.exists(destination_uri):
                return RasterOperationOut(
                    local_path=None,
                    destination_uri=destination_uri,
                    presigned_url=self._presigned_url(store, destination_uri),
                    write_back=False,
                    publish_catalog=False,
                )

            return None

        if not self.overwrite and self.local_path.is_file():
            return RasterOperationOut(
                local_path=str(self.local_path),
                destination_uri=None,
                presigned_url=None,
                write_back=False,
                publish_catalog=False,
            )

        return None

    def complete(self, result_path: str | Path) -> RasterOperationOut:
        """Upload remote outputs and build the normalized tool result."""

        local_path = Path(result_path)

        if not self.is_remote:
            return RasterOperationOut(
                local_path=str(local_path),
                destination_uri=None,
                presigned_url=None,
                write_back=True,
                publish_catalog=False,
            )

        destination_uri = self.destination_uri or ""
        store = self._require_store(destination_uri)
        store.put(local_path, destination_uri, overwrite=self.overwrite)
        return RasterOperationOut(
            local_path=str(local_path),
            destination_uri=destination_uri,
            presigned_url=self._presigned_url(store, destination_uri),
            write_back=True,
            publish_catalog=False,
        )

    def _require_store(self, destination_uri: str) -> Any:
        if self.store is None:
            raise ValueError(f"S3 output {destination_uri} requires ToolContext.store.")
        return self.store

    def _presigned_url(self, store: Any, destination_uri: str) -> str | None:
        if not self.presign_url:
            return None
        return store.presign(destination_uri, expires_in=self.presign_expires_in).url


def _is_s3_output(output_file: str | None) -> bool:
    return output_file is not None and urlparse(output_file).scheme.lower() == "s3"


__all__ = [
    "RasterOperationIn",
    "RasterOperationOut",
    "RasterOutput",
]
