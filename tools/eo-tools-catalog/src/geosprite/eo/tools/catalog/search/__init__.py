from __future__ import annotations

from geosprite.eo.catalog.reader import CatalogReaderRegistry, CatalogReadService
from geosprite.eo.catalog.protocols.stac.reader import StacCatalogBackend

_catalog_service = None
_stac_backend = None


def get_stac_backend() -> StacCatalogBackend:
    global _stac_backend
    if _stac_backend is None:
        _stac_backend = StacCatalogBackend()
    return _stac_backend


def get_catalog_service() -> CatalogReadService:
    global _catalog_service
    if _catalog_service is None:
        registry = CatalogReaderRegistry()
        registry.register(get_stac_backend())
        _catalog_service = CatalogReadService(registry)
    return _catalog_service


catalog_service = get_catalog_service()
