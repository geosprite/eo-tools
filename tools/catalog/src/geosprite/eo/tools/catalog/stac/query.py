# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import dataclass

@dataclass
class Query:
    """Base STAC Query class."""
    collection: str
    datetime: str = None
    bbox: str = None
    geometry: str = None
    assets: list[str] = None

    def parameters(self, **kwargs):
        """Convert query to STAC API parameters."""
        kwargs = kwargs if kwargs is not None else {}

        kwargs["collections"] = [self.collection]
        kwargs["datetime"] = self.datetime

        if self.bbox:
            kwargs["bbox"] = self.bbox

        if self.geometry:
            kwargs["intersects"] = self.geometry

        return kwargs
