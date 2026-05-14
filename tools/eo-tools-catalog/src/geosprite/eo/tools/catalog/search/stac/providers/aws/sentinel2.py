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

        item = Item(**super().parse(args).__dict__)
        item.cloud_cover = stac_item.properties.get('eo:cloud_cover')
        grid_code = stac_item.properties.get('grid:code', '')
        item.tile = grid_code[5:] if len(grid_code) > 5 else None
        item.nodata_percent = stac_item.properties.get('s2:nodata_pixel_percentage')

        return item

    @classmethod
    def s3_to_https(cls, s3_uri: str, https_domain: str = "s3.eu-central-1.amazonaws.com"):
        return super().s3_to_https(s3_uri, https_domain)


@dataclass
class Query(Query):
    cloud_cover: str = None
    tile: str = None
    nodata_percent: str = None

    @staticmethod
    def of(query):
        return Query(**query.__dict__)

    def parameters(self, **kwargs):
        kwargs = super().parameters(**kwargs)

        query = kwargs.get('query', {})

        if isinstance(self.cloud_cover, str):
            query["eo:cloud_cover"] = {"lte": self.cloud_cover}

        if isinstance(self.tile, str):
            tile_len = len(self.tile)

            if tile_len == 5:
                query["grid:code"] = {"eq": f"MGRS-{self.tile}"}
            else:
                if tile_len >= 2:
                    query["mgrs:utm_zone"] = {"eq": int(self.tile[:2])}

                    if tile_len >= 3:
                        query["mgrs:latitude_band"] = {"eq": self.tile[2:3]}

        if self.nodata_percent:
            query["s2:nodata_pixel_percentage"] = {"lte": self.nodata_percent}

        if len(query) > 0:
            kwargs["query"] = query

        return kwargs


class Sen2Collection(Collection):
    """Collection for Sentinel-2 datasets in Element 84."""
    
    @property
    def prefix(self) -> str:
        return "sentinel-2"
    
    def create_query(self, collection: str, **kwargs):
        return Query(collection=collection, **kwargs)
    
    def parse_item(self, args: tuple):
        return Item.parse(args)
