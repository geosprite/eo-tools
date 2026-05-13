"""eo-stac: STAC asset and item models for Earth Observation Tools."""

from .assets import DEFAULT_MEDIA_TYPE, Asset, AssetCollection
from .builder import build_collection, build_item_from_assets, collection_to_stac_dict, item_to_stac_dict
from .collections import Collection, Extent, SpatialExtent, TemporalExtent, collection_extent
from .items import Item, ItemCollection, Link, StacFeature, StacFeatureCollection, StacLink

__all__ = [
    "Asset",
    "AssetCollection",
    "Collection",
    "DEFAULT_MEDIA_TYPE",
    "Extent",
    "Item",
    "ItemCollection",
    "Link",
    "SpatialExtent",
    "StacFeature",
    "StacFeatureCollection",
    "StacLink",
    "TemporalExtent",
    "build_collection",
    "build_item_from_assets",
    "collection_extent",
    "collection_to_stac_dict",
    "item_to_stac_dict",
]

__version__ = "0.1.0"
