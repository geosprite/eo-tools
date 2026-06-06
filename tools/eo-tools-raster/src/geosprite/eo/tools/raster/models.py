"""Shared raster tool input and output models."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RasterOperationIn(BaseModel):
    """Shared local IO controls for raster tools."""

    model_config = ConfigDict(extra="forbid")

    input_files: list[str] = Field(
        min_length=1,
        description="Raster input paths or URIs passed directly to eo-raster.",
    )
    localization_bucket: str | None = Field(
        default=None,
        description=(
            "Optional S3 bucket used to localize remote input_files before processing. "
            "When set, operators receive localized s3:// URIs; when omitted, URI "
            "inputs are fetched to the runtime workspace."
        ),
    )
    localization_prefix: str = Field(
        default="eo-store/localized",
        description="S3 object key prefix used with localization_bucket.",
    )
    output_file: str | None = Field(
        default=None,
        description=(
            "Raster output target. Local paths write locally; s3:// outputs are not supported."
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
        description="Unsupported by direct eo-raster execution.",
    )
    presign_expires_in: int = Field(
        default=3600,
        ge=1,
        description="Reserved for compatibility; presign_url is not supported.",
    )

    @model_validator(mode="after")
    def _validate_output_policy(self) -> "RasterOperationIn":
        if _is_s3_output(self.output_file):
            raise ValueError("output_file must be a local path for direct eo-raster execution.")
        if self.presign_url:
            raise ValueError("presign_url is not supported by direct eo-raster execution.")
        return self


class RasterOperationOut(BaseModel):
    """Normalized raster tool result."""

    local_path: str | None = Field(
        default=None,
        description="Local raster output path.",
    )
    destination_uri: str | None = Field(
        default=None,
        description="Always null for direct eo-raster execution.",
    )
    presigned_url: str | None = Field(
        default=None,
        description="Always null for direct eo-raster execution.",
    )
    write_back: bool = Field(description="Whether this request wrote a new output.")
    publish_catalog: bool = Field(description="Whether Catalog publication ran.")


def local_output_path(workdir: Path, output_file: str | None, fallback: str) -> Path:
    """Resolve the local output path required by direct eo-raster operations."""

    if _is_s3_output(output_file):
        raise ValueError(
            "Direct eo-raster execution requires a local output_file; "
            "stage s3:// outputs outside eo-tools-raster."
        )
    if output_file is not None:
        path = Path(output_file)
        return path if path.is_absolute() else workdir / path
    return workdir / "raster" / uuid4().hex / fallback


def _is_s3_output(output_file: str | None) -> bool:
    return output_file is not None and urlparse(output_file).scheme.lower() == "s3"


__all__ = [
    "RasterOperationIn",
    "RasterOperationOut",
    "local_output_path",
]
