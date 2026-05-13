# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from typing import Callable
from pystac import Asset

from .item import Item
from .query import Query


class StacClient:
    """Base STAC client for communicating with STAC APIs."""

    def __init__(self, url: str, retry_times: int = 5, **kwargs):
        from pystac_client import Client
        from pystac_client.stac_api_io import StacApiIO

        self.client = Client.open(url=url, stac_io=StacApiIO(max_retries=retry_times, **kwargs))

    def search_items(self, query: Query, parse_item: Callable, **kwargs) -> list:
        """Search items using query."""
        search = self.client.search(**query.parameters(**kwargs))

        items = list(search.items())
        if not items:
            return []

        return list(map(parse_item, ((item, query.assets) for item in items)))

    def get_item(self, item_id: str, parse_item: Callable, assets: list[str] = None) -> Item:
        """Get single item by ID."""
        return parse_item((next(self.client.get_items(item_id)), assets))

    def get_assets(self, collection: str) -> dict[str, Asset]:
        """Get available assets for collection."""
        pass

    def search(self, query: Query, **kwargs) -> list:
        """Search method to be implemented by subclasses."""
        raise NotImplementedError()
