# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from typing import List, Dict

from pystac import Asset

from ...client import StacClient
from ...collection import CollectionRegistry
from ...item import Item
from .landsat import LandsatCollection
from ...provider import Provider
from ...query import Query
from .sentinel1 import Sen1Collection
from .sentinel2 import Sen2Collection

__all__ = ["Element84Provider"]


class Element84Provider(Provider):
    """Element 84 Earth Search STAC provider.
    
    Element 84's Earth Search is a STAC compliant search and discovery API built using
    Filmdrop services bringing petabytes worth of Geospatial Open Datasets
    from Registry of Open Data on AWS.
    
    Provides access to Sentinel-1, Sentinel-2, and Landsat data.
    """
    
    def __init__(self):
        self.client = StacClient(self.endpoint_url)
        self.collection_registry = CollectionRegistry()

        """Register collection handlers for loose coupling."""
        self.collection_registry.register(Sen2Collection())
        self.collection_registry.register(Sen1Collection())
        self.collection_registry.register(LandsatCollection())
    
    @property
    def endpoint_url(self) -> str:
        return "https://earth-search.aws.element84.com/v1"
    
    def get_supported_collections(self) -> List[str]:
        return ["sentinel-2", "sentinel-1", "landsat"]
    
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
        return handler.parse_item(args)
    
    def search(self, query: Query, **kwargs) -> List[Item]:
        """Search items using the query."""
        return self.client.search_items(query, self.parse_item, **kwargs)
    
    def get_item(self, collection: str, item_id: str, assets: List[str] = None) -> Item:
        """Get single item by ID."""
        return self.client.get_item(item_id, self.parse_item, assets)
    
    def get_asset_names(self, collection: str) -> Dict[str, Asset]:
        """Get available asset names for collection."""
        return self.client.client.get_collection(collection).extra_fields.get('item_assets')
