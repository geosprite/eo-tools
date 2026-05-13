# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from typing import List, Tuple

from osgeo import gdal, ogr

class GeoTransformHelper:
    """
    Utility for converting between pixel coordinates and geographic coordinates
    using a GDAL GeoTransform (affine transformation coefficients).
    """

    def __init__(self, transform: List[float]):
        self.transform = transform

    def to_xy(self, x_geo: float, y_geo: float) -> Tuple[int, int]:
        """Convert geographic coordinates to pixel coordinates."""
        return tuple(map(int, gdal.ApplyGeoTransform(gdal.InvGeoTransform(self.transform), x_geo, y_geo)))

    def to_geo_xy(self, x: int, y: int) -> Tuple[float, float]:
        """Convert pixel coordinates to geographic coordinates."""
        return gdal.ApplyGeoTransform(self.transform, x, y)

    def to_geo_window(self, window: Tuple[int, int, int, int]) -> Tuple[float, ...]:
        """Convert a pixel-space window to a geographic GeoTransform."""
        x_off, y_off = self.to_geo_xy(window[0], window[2])
        window_transform = list(self.transform)
        window_transform[0] = x_off
        window_transform[3] = y_off
        return tuple(window_transform)

    def to_geo_envelope(self, geometry: ogr.Geometry) -> List[int]:
        """Convert a geometry envelope to pixel-space bounding coordinates."""
        min_x, max_x, min_y, max_y = geometry.GetEnvelope()
        x_start, y_start = self.to_xy(min_x, max_y)
        x_end, y_end = self.to_xy(max_x, min_y)
        return [x_start, x_end, y_start, y_end]
