from __future__ import annotations

from typing import Any

from geosprite.eo.catalog import CatalogRegistry, CatalogSearchRequest, CatalogService, ItemCollection
from geosprite.eo.catalog.protocols.stac import StacCatalogBackend

_mgrs = None
_catalog_service = None
_stac_backend = None


def _mgrs_bounds(tile: str):
    global _mgrs
    if _mgrs is None:
        from geosprite.eo.tools.catalog.grs.core.mgrs.dao import MGRS

        _mgrs = MGRS()
    return _mgrs.bounds([tile])


def get_stac_backend() -> StacCatalogBackend:
    global _stac_backend
    if _stac_backend is None:
        _stac_backend = StacCatalogBackend(tile_bounds_resolver=_mgrs_bounds)
    return _stac_backend


def get_catalog_service() -> CatalogService:
    global _catalog_service
    if _catalog_service is None:
        registry = CatalogRegistry()
        registry.register_backend("stac", get_stac_backend())
        _catalog_service = CatalogService(registry)
    return _catalog_service


def execute_search(collection: str, query_kwargs: dict[str, Any], provider: str | None = None) -> ItemCollection:
    return get_catalog_service().search(
        CatalogSearchRequest(
            collection=collection,
            provider=provider,
            **query_kwargs,
        )
    )
