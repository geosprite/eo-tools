"""Compatibility import surface for STAC item DTOs.

Prefer importing from ``geosprite.eo.core`` or ``geosprite.eo.core.items`` in
new code.
"""

from .items import Item, ItemCollection

__all__ = [
    "Item",
    "ItemCollection",
]
