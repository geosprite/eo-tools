# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from typing import List, Dict
from pystac import Asset

from ...provider import Provider
from ...client import StacClient
from ...item import Item
from ...query import Query
from ...collection import CollectionRegistry
from .sentinel1 import Sen1Collection
from .sentinel2 import Sen2Collection
from .modis import ModisCollection
from .landsat import LandsatCollection


__all__ = ["PlanetaryComputerProvider"]


def _asset_descriptor(href: str) -> dict[str, object]:
    return {
        "href": href,
        "provider": "planetarycomputer",
        "requires_signing": True,
        "signer": "planetarycomputer",
    }


class PlanetaryComputerProvider(Provider):
    """Microsoft Planetary Computer STAC provider.
    
    Provides access to Sentinel-2, MODIS, and other datasets
    through Microsoft Planetary Computer endpoint.
    """
    
    def __init__(self):
        self.client = StacClient(self.endpoint_url)
        self.collection_registry = CollectionRegistry()

        """Register collection handlers for loose coupling."""
        self.collection_registry.register(Sen1Collection())
        self.collection_registry.register(Sen2Collection())
        self.collection_registry.register(ModisCollection())
        self.collection_registry.register(LandsatCollection())
    
    @property
    def endpoint_url(self) -> str:
        return "https://planetarycomputer.microsoft.com/api/stac/v1"
    
    def get_supported_collections(self) -> List[str]:
        return ["sentinel-1", "sentinel-2", "modis", "landsat"]
    
    def create_query(self, collection: str, **kwargs) -> Query:
        """Create provider-specific query object using registry."""
        handler = self.collection_registry.find(collection)
        if not handler:
            raise ValueError(f"Unsupported collection: {collection}")
        return handler.create_query(collection, **kwargs)
    
    def parse_item(self, args: tuple) -> Item:
        """Parse STAC item using registry."""
        stac_item, assets = args
        collection = stac_item.collection_id
        handler = self.collection_registry.find(collection)
        if not handler:
            raise ValueError(f"Unsupported collection: {collection}")
        item = handler.parse_item((stac_item, assets))
        if item.assets:
            item.assets = {
                key: _asset_descriptor(href) if isinstance(href, str) else href
                for key, href in item.assets.items()
            }
        return item
    
    def search(self, query: Query, **kwargs) -> List[Item]:
        """Search items using the query."""
        return self.client.search_items(query, self.parse_item, **kwargs)
    
    def get_item(self, collection: str, item_id: str, assets: List[str] = None) -> Item:
        """Get single item by ID."""
        return self.client.get_item(item_id, self.parse_item, assets)
    
    def get_asset_names(self, collection: str) -> Dict[str, Asset]:
        """Get available asset names for collection."""
        return self.client.client.get_collection(collection).extra_fields.get('item_assets')
