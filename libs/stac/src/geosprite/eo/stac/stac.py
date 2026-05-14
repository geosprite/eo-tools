"""Compatibility import surface for STAC item DTOs.

Prefer importing from ``geosprite.eo.eo-tools-core`` or ``geosprite.eo.eo-tools-core.items`` in
new code.
"""

from .items import Item, ItemCollection

__all__ = [
    "Item",
    "ItemCollection",
]
