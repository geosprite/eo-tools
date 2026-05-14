from dataclasses import dataclass

from pystac import Item as StacItem

from ...item import Item
from ...query import Query
from ...collection import Collection

__all__ = ["Item", "Query", "LandsatCollection"]


def _format_tile(path: int | str | None, row: int | str | None) -> str | None:
    if path is None or row is None:
        return None

    return f"{int(path):03d}/{int(row):03d}"


def _parse_tile(tile: str | None) -> tuple[int, int] | tuple[None, None]:
    if not isinstance(tile, str):
        return None, None

    normalized = tile.strip().replace("_", "/")
    if "/" in normalized:
        path_str, row_str = normalized.split("/", 1)
    elif len(normalized) == 6 and normalized.isdigit():
        path_str, row_str = normalized[:3], normalized[3:]
    else:
        return None, None

    if not (path_str.isdigit() and row_str.isdigit()):
        return None, None

    return int(path_str), int(row_str)


def _parse_cloud_cover(value) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class Item(Item):
    cloud_cover: float = None
    tile: str = None
    path: int = None
    row: int = None

    @classmethod
    def parse(cls, args: tuple[StacItem, list[str]]):
        stac_item, assets = args

        item = Item(**super().parse(args).__dict__)
        properties = stac_item.properties

        item.cloud_cover = properties.get("eo:cloud_cover")

        def _to_int(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        path = _to_int(properties.get("landsat:wrs_path"))
        row = _to_int(properties.get("landsat:wrs_row"))

        item.path = path
        item.row = row
        item.tile = f"{path:03d}/{row:03d}" if path is not None and row is not None else None

        return item


@dataclass
class Query(Query):
    cloud_cover: float | str = None
    tile: str = None

    @staticmethod
    def of(query):
        return Query(**query.__dict__)

    def parameters(self, **kwargs):
        kwargs = super().parameters(**kwargs)

        query = kwargs.get("query", {})

        cloud_cover = _parse_cloud_cover(self.cloud_cover)
        if cloud_cover is not None:
            query["eo:cloud_cover"] = {"lte": cloud_cover}

        path, row = _parse_tile(self.tile)
        if path is not None and row is not None:
            query["landsat:wrs_path"] = {"eq": f"{path:03d}"}
            query["landsat:wrs_row"] = {"eq": f"{row:03d}"}

        if query:
            kwargs["query"] = query

        return kwargs


class LandsatCollection(Collection):
    """Collection for Landsat datasets in Element 84."""
    
    @property
    def prefix(self) -> str:
        return "landsat"
    
    def create_query(self, collection: str, **kwargs):
        return Query(collection=collection, **kwargs)
    
    def parse_item(self, args: tuple):
        return Item.parse(args)
