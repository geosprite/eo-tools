from __future__ import annotations

import json
import re
from typing import Any, ClassVar

from geosprite.eo.stac import Asset, AssetCollection
from geosprite.eo.tools import Tool
from geosprite.eo.store import auto_minio_download


class BaseRasterTool(Tool):
    version: ClassVar[str] = "1.0.0"
    requires: ClassVar[list[str]] = ["gdal"]


def extract_urls(text: str) -> list[str]:
    try:
        data = json.loads(text)
        text = json.dumps(data)
        pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=&%]*"
    except json.JSONDecodeError:
        pattern = r"https?://[^\s\"']+"
    return list(set(re.findall(pattern, text)))


@auto_minio_download(urls_param="inputs")
async def resolve_input_urls(inputs: list[str]) -> list[str]:
    return inputs


async def resolve_input_url(input_url: str) -> str:
    return (await resolve_input_urls([input_url]))[0]


def raster_asset(
    href: str,
    *,
    title: str | None = None,
    role: str = "data",
    **extra: Any,
) -> Asset:
    return Asset(
        href=href,
        roles=[role],
        title=title,
        extra_fields={key: value for key, value in extra.items() if value is not None},
    )


def raster_asset_collection(
    urls: list[str],
    *,
    cache_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AssetCollection:
    return AssetCollection(
        items=[raster_asset(url) for url in urls],
        cache_key=cache_key,
        metadata=metadata or {},
    )
