# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pystac import Item as StacItem


@dataclass
class Item:
    """Base STAC Item class."""
    id: str
    datetime: datetime
    assets: dict[str, object] = None
    geometry: dict[str, Any] | None = None

    def __repr__(self):
        return f"{self.id}, {self.datetime}"

    @classmethod
    def parse(cls, args: tuple[StacItem, list[str]]):
        """Parse STAC item into base Item object."""
        stac_item, assets = args

        item = Item(stac_item.id, stac_item.datetime)
        item.geometry = stac_item.geometry

        if isinstance(assets, list):
            keys = stac_item.assets.keys()
            item.assets = {k: stac_item.assets[k].href for k in assets if k in keys}
        else:
            item.assets = {k: stac_item.assets[k].href for k in stac_item.assets}

        return item
