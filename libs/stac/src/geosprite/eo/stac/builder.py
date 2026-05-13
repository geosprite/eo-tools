"""Compatibility imports for STAC build and serialization helpers.

Prefer importing new code from ``geosprite.eo.core.assets``,
``geosprite.eo.core.items``, or ``geosprite.eo.core.collections``.
"""

from .assets import asset_to_stac_dict
from .collections import build_collection, collection_to_stac_dict
from .items import build_item_from_assets, item_to_stac_dict

__all__ = [
    "asset_to_stac_dict",
    "build_collection",
    "build_item_from_assets",
    "collection_to_stac_dict",
    "item_to_stac_dict",
]
