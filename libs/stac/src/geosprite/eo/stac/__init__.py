"""eo-stac: STAC asset and item models for Earth Observation Tools."""

from .assets import DEFAULT_MEDIA_TYPE, Asset, asset_to_stac_dict
from .collections import (
    Collection,
    Extent,
    SpatialExtent,
    TemporalExtent,
    build_collection,
    collection_extent,
    collection_to_stac_dict,
)
from .items import Item, ItemCollection, build_item_from_assets, item_to_stac_dict

__all__ = [
    "Asset",
    "asset_to_stac_dict",
    "Collection",
    "DEFAULT_MEDIA_TYPE",
    "Extent",
    "Item",
    "ItemCollection",
    "SpatialExtent",
    "TemporalExtent",
    "build_collection",
    "build_item_from_assets",
    "collection_extent",
    "collection_to_stac_dict",
    "item_to_stac_dict",
]

__version__ = "0.1.0"
