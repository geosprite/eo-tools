from shapely.geometry import Polygon, GeometryCollection

from ..grid import SpatialGridSystem, Batch

__all__ = ["WGRS"]


class WGRS(SpatialGridSystem):
    """
    WGRS: World Grid Reference System 经纬度格网
    """

    def __init__(self, deg: int = 5, batch: int = -1):
        self.deg = deg
        self.batch = Batch(batch_size=batch)

    def get_tiles(self, geom: GeometryCollection, **kwargs) -> dict:

        def next_coord(start, end):
            while start < end:
                yield start
                start += self.deg

        x_min, y_min, x_max, y_max = geom.bounds

        for x1 in next_coord(x_min, x_max):
            for y1 in next_coord(y_min, y_max):

                _lng = f"E{int(x1):03d}" if x1 >= 0 else f"W{-int(x1):03d}"
                _lat = f"N{int(y1):02d}" if y1 >= 0 else f"S{-int(y1):02d}"
                grid_id = f"{_lng}{_lat}"

                x2 = x1 + self.deg if x1 + self.deg <= x_max else x_max
                y2 = y1 + self.deg if y1 + self.deg <= y_max else y_max

                grid_geom = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

                intersection = geom.intersection(grid_geom)

                if intersection.is_empty:
                    continue

                bbox = intersection.bounds

                if self.batch.add(key=grid_id, bbox=bbox, **kwargs):
                    yield self.batch.tiles
                    self.batch.reset_tiles()

        yield self.batch.tiles
