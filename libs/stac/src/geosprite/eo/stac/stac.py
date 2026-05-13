"""Compatibility import surface for STAC item DTOs.

Prefer importing from ``geosprite.eo.stac`` or ``geosprite.eo.stac.items`` in
new code.
"""

from .items import Item, ItemCollection, Link, StacFeature, StacFeatureCollection, StacLink

__all__ = [
    "Link",
    "Item",
    "ItemCollection",
    "StacLink",
    "StacFeature",
    "StacFeatureCollection",
]
