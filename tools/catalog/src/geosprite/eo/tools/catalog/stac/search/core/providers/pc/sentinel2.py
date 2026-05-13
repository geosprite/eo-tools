# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import dataclass

from pystac import Item as StacItem

from ...collection import Collection
from ...item import Item
from ...query import Query

__all__ = ['Item', 'Query', 'Sen2Collection']


@dataclass
class Item(Item):
    cloud_cover: float = None
    tile: str = None
    nodata_percent: float = None

    def __repr__(self):
        return super().__repr__() + f", {self.cloud_cover}"

    @classmethod
    def parse(cls, args: tuple[StacItem, list[str]]):
        stac_item, assets = args

        item = super().parse(args)

        item.cloud_cover = stac_item.properties.get('eo:cloud_cover')
        item.tile = stac_item.properties.get('s2:mgrs_tile')
        item.nodata_percent = stac_item.properties.get('s2:nodata_pixel_percentage')

        return item


@dataclass
class Query(Query):
    cloud_cover: str = None
    tile: str = None

    @staticmethod
    def of(query):
        return Query(**query.__dict__)

    def parameters(self, **kwargs):
        kwargs = super().parameters(**kwargs)

        query = kwargs.get('query', {})

        if isinstance(self.cloud_cover, str):
            query["eo:cloud_cover"] = {"lte": self.cloud_cover}

        if isinstance(self.tile, str):
            query['s2:mgrs_tile'] = {"eq": self.tile}

        if len(query) > 0:
            kwargs["query"] = query

        kwargs['sortby'] = "s2:mgrs_tile,-properties.ee:cloud_cover"

        return kwargs


class Sen2Collection(Collection):
    """Collection for Sentinel-2 datasets in Planetary Computer."""
    
    @property
    def prefix(self) -> str:
        return "sentinel-2"
    
    def create_query(self, collection: str, **kwargs):
        return Query(collection=collection, **kwargs)
    
    def parse_item(self, args: tuple):
        return Item.parse(args)
