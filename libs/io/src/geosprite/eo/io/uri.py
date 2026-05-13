"""URI parsing utilities for Earth Observation Tools.

Supported schemes (scaffold — full materialisation handled by `store.py`):

| Scheme            | Example                                  | Notes                        |
| ----------------- | ---------------------------------------- | ---------------------------- |
| `file://`         | `file:///data/scene.tif`                 | Local filesystem.            |
| `http(s)://`      | `https://host/path/scene.tif`            | Streaming via fsspec/HTTP.   |
| `s3://`           | `s3://bucket/path/scene.tif`             | Requires `eo-io[s3]`.        |
| `gs://`           | `gs://bucket/path/scene.tif`             | Requires `eo-io[gcs]`.       |
| `az://`           | `az://container/path/scene.tif`          | Requires `eo-io[azure]`.     |
| `store://<path>`  | `store://preprocessing/abc/iw-vv.tif`    | Logical, resolved by Store.  |
| `/vsi*` (no //)   | `/vsis3/bucket/path/scene.tif`           | GDAL VSI; passed to rasterio |
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

VSI_PREFIXES: tuple[str, ...] = (
    "/vsicurl/",
    "/vsis3/",
    "/vsigs/",
    "/vsiaz/",
    "/vsimem/",
    "/vsizip/",
    "/vsitar/",
    "/vsigzip/",
)


@dataclass(frozen=True)
class URI:
    """Parsed URI with eo-tools-aware semantics."""

    scheme: str
    netloc: str
    path: str
    raw: str

    @property
    def is_remote(self) -> bool:
        return self.scheme in {"http", "https", "s3", "gs", "az"}

    @property
    def is_logical(self) -> bool:
        """A `store://...` URI that needs resolution by a `StoreClient`."""
        return self.scheme == "store"

    @property
    def is_vsi(self) -> bool:
        """A bare GDAL `/vsi*` path (no scheme)."""
        return self.scheme == "" and self.raw.startswith(VSI_PREFIXES)


def parse_uri(uri: str) -> URI:
    """Parse a URI string into a `URI` dataclass.

    Bare local paths (no scheme) are returned with `scheme=""`. GDAL `/vsi*`
    paths are recognised so callers can short-circuit to rasterio.
    """
    if not uri:
        raise ValueError("URI must be non-empty")

    if uri.startswith(VSI_PREFIXES):
        return URI(scheme="", netloc="", path=uri, raw=uri)

    parsed = urlparse(uri)
    return URI(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=parsed.path,
        raw=uri,
    )
