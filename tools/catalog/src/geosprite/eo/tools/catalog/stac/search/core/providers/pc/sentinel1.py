# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import dataclass
from typing import List

from pystac import Item as StacItem

from ......grs.core.mgrs.dao import MGRS
from ...collection import Collection
from ...item import Item
from ...query import Query

__all__ = ['Item', 'Query', 'Sen1Collection']

_mgrs = None


def get_mgrs():
    global _mgrs
    if _mgrs is None:
        _mgrs = MGRS()
    return _mgrs


@dataclass
class Item(Item):
    orbit_state: str = None  # ascending/descending
    polarizations: List[str] = None  # ['VV', 'VH']
    instrument_mode: str = None  # IW, EW, SM
    product_type: str = None  # GRD
    resolution: str = None  # full, high, medium

    @classmethod
    def parse(cls, args: tuple[StacItem, list[str]]):
        stac_item, assets = args

        item = Item(**super().parse(args).__dict__)

        item.orbit_state = stac_item.properties.get('sat:orbit_state')
        item.polarizations = stac_item.properties.get('sar:polarizations')
        item.instrument_mode = stac_item.properties.get('sar:instrument_mode')
        item.product_type = stac_item.properties.get('sar:product_type')
        item.resolution = stac_item.properties.get('s1:resolution')

        return item


@dataclass
class Query(Query):
    orbit_state: str = None
    tile: str = None

    @staticmethod
    def of(query):
        return Query(**query.__dict__)

    def parameters(self, **kwargs):
        kwargs = super().parameters(**kwargs)

        query = kwargs.get('query', {})

        if self.tile and "bbox" not in kwargs and "intersects" not in kwargs:
            mgrs = get_mgrs()
            kwargs["bbox"] = ",".join([str(i) for i in mgrs.bounds([self.tile])])

        if isinstance(self.orbit_state, str):
            orbit_state = self.orbit_state.lower()
            if orbit_state in ['ascending', 'descending']:
                query["sat:orbit_state"] = {"eq": orbit_state}

        if len(query) > 0:
            kwargs["query"] = query

        return kwargs


class Sen1Collection(Collection):
    """Collection for Sentinel-1 datasets in Planetary Computer."""

    @property
    def prefix(self) -> str:
        return "sentinel-1"

    def create_query(self, collection: str, **kwargs):
        return Query(collection=collection, **kwargs)

    def parse_item(self, args: tuple):
        return Item.parse(args)
