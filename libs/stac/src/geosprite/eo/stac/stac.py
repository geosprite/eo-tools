"""Compatibility import surface for STAC item DTOs.

Prefer importing from ``geosprite.eo.stac`` or ``geosprite.eo.stac.items`` in
new code.
"""

from .items import Item, ItemCollection

__all__ = [
    "Item",
    "ItemCollection",
]
