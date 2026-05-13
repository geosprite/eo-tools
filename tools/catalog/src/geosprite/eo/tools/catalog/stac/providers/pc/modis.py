# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import dataclass

from pystac import Item as StacItem

from ...item import Item
from ...query import Query
from ...collection import Collection

__all__ = ['Item', 'Query', 'ModisCollection']


@dataclass
class Item(Item):
    cloud_cover: float = None
    tile: str = None

    def __repr__(self):
        return super().__repr__() + f", {self.cloud_cover}"

    @classmethod
    def parse(cls, args: tuple[StacItem, list[str]]):
        stac_item, _ = args

        item = super().parse(args)

        item.cloud_cover = stac_item.properties.get('s2:cloud_cover')
        item.tile = stac_item.properties.get('s2:mgrs_tile')

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
            pos = self.tile.find("v")
            h, v = int(self.tile[1:pos]), int(self.tile[pos + 1:])

            query['modis:horizontal-tile'] = {"eq": h}
            query['modis:vertical-tile'] = {"eq": v}

        return kwargs


class ModisCollection(Collection):
    """Collection for MODIS datasets in Planetary Computer."""
    
    @property
    def prefix(self) -> str:
        return "modis"
    
    def create_query(self, collection: str, **kwargs):
        return Query(collection=collection, **kwargs)
    
    def parse_item(self, args: tuple):
        return Item.parse(args)
