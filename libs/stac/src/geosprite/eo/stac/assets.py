"""Small STAC-like asset schemas used by Earth Observation Tools.

The names and field shape intentionally mirror the common parts of pystac,
but this package does not depend on pystac. Only fields currently used by
eo-tools services are modeled here; provider-specific or extension fields go
into ``extra_fields``.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

DEFAULT_MEDIA_TYPE = "image/tiff; application=geotiff; profile=cloud-optimized"


class Asset(BaseModel):
    """One addressable artifact, similar to ``pystac.Asset``."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    href: str = Field(
        ...,
        description="Asset URI or path. Supports http(s), s3, gs, az, store, file and GDAL VSI paths.",
        validation_alias=AliasChoices("href", "uri"),
        serialization_alias="href",
    )
    media_type: str = Field(
        default=DEFAULT_MEDIA_TYPE,
        alias="type",
        description="IANA media type, serialized as STAC asset field `type`.",
    )
    roles: list[str] | None = Field(default=None, description="STAC asset roles, e.g. ['data'].")
    title: str | None = None
    description: str | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "href" not in data and "uri" in data:
            data["href"] = data.pop("uri")
        if "type" not in data and "media_type" in data:
            data["type"] = data.pop("media_type")
        if "roles" not in data and "role" in data:
            role = data.pop("role")
            data["roles"] = [role] if isinstance(role, str) else role
        if "extra_fields" not in data and "extra" in data:
            data["extra_fields"] = data.pop("extra")
        return data

    @property
    def uri(self) -> str:
        """Backward-compatible alias while services migrate to ``href``."""
        return self.href


def asset_to_stac_dict(asset: Asset) -> dict[str, Any]:
    """Serialize an Asset and flatten extra_fields into STAC extension fields."""

    data = asset.model_dump(by_alias=True, exclude_none=True)
    extra = data.pop("extra_fields", None) or {}
    data.update(extra)
    return data


__all__ = ["Asset", "DEFAULT_MEDIA_TYPE", "asset_to_stac_dict"]
