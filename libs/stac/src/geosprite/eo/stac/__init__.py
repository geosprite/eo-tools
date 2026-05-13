"""eo-stac: STAC asset and item models for Earth Observation Tools."""

from .assets import DEFAULT_MEDIA_TYPE, Asset, AssetCollection
from .items import Item, ItemCollection, Link, StacFeature, StacFeatureCollection, StacLink

__all__ = [
    "Asset",
    "AssetCollection",
    "DEFAULT_MEDIA_TYPE",
    "Item",
    "ItemCollection",
    "Link",
    "StacFeature",
    "StacFeatureCollection",
    "StacLink",
]

__version__ = "0.1.0"
