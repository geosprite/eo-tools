# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import os
import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Optional, Union
from osgeo import gdal, osr
from concurrent.futures import ThreadPoolExecutor

gdal.UseExceptions()

# Global thread pool for CPU-bound numpy operations if needed
_executor = ThreadPoolExecutor()


class SlidingWindow:
    """
    Iterator for sliding windows (tiles) over a raster dataset.
    Generates window tuples (x_off, y_off, width, height) for block-based processing.
    """
    def __init__(self,
                 raster_shape: Union[int, Tuple[int, int]],
                 window_shape: Union[int, Tuple[int, int]],
                 x_start: int = 0, y_start: int = 0):
        raster_h, raster_w = (raster_shape, raster_shape) if isinstance(raster_shape, int) else raster_shape
        win_h, win_w = (window_shape, window_shape) if isinstance(window_shape, int) else window_shape

        if x_start >= raster_w or y_start >= raster_h:
            raise ValueError("Start position exceeds raster dimensions")

        d, m = divmod(raster_h, win_h)
        self.n_rows = d + int(m > 0)
        d, m = divmod(raster_w, win_w)
        self.n_cols = d + int(m > 0)

        self.x_start = x_start
        self.y_start = y_start
        self.height = win_h
        self.width = win_w
        self.raster_height = raster_h
        self.raster_width = raster_w
        self.j = 0
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        cur = self.current
        if cur is None:
            raise StopIteration

        self.i += 1
        if self.i >= self.n_cols:
            self.j += 1
            self.i = 0
        return cur

    @property
    def current(self) -> tuple[int, int, int, int] | None:

        if self.j < self.n_rows and self.i < self.n_cols:
            x_off = self.i * self.width
            x_size = min(self.width, self.raster_width - x_off)
            x_off += self.x_start

            y_off = self.j * self.height
            y_size = min(self.height, self.raster_height - y_off)
            y_off += self.y_start
        else:
            return None

        return x_off, y_off, x_size, y_size

    @staticmethod
    def buffer(window: Tuple[int, int, int, int], image_size: Tuple[int, int], buffer_size: int) -> Tuple[int, int, int, int]:
        """Apply buffer to a window, clipping to image boundaries."""
        win_w_off, win_h_off, win_w_size, win_h_size = window
        image_h_size, image_w_size = image_size
        buffer_h_size, buffer_w_size = buffer_size, buffer_size

        def get_offset(win_off: int, win_sz: int, buf_sz: int, img_sz: int) -> Tuple[int, int]:
            if win_off <= buf_sz:
                off = 0
                size = min(win_off + win_sz + buf_sz, img_sz)
            else:
                off = win_off - buf_sz
                size = min(win_sz + buf_sz * 2, img_sz - off)
            return off, size

        h_off, h_size = get_offset(win_h_off, win_h_size, buffer_h_size, image_h_size)
        w_off, w_size = get_offset(win_w_off, win_w_size, buffer_w_size, image_w_size)

        return w_off, h_off, w_size, h_size

    @staticmethod
    def unbuffer(window: tuple[int, int, int, int], data_size: tuple[int, int], buffer_size: int) -> tuple[int, int, int, int]:
        win_w_off, win_h_off, win_w_size, win_h_size = window
        data_h_size, data_w_size = data_size
        buffer_h_size, buffer_w_size = buffer_size, buffer_size

        def get_start_end(win_off: int, win_sz: int, dat_sz: int, buffer_sz: int):

            if win_off <= buffer_sz:
                start = win_off
                end = win_off + win_sz
            elif win_sz + buffer_sz <= dat_sz <= win_sz + buffer_sz * 2:
                start = buffer_sz
                end = win_sz + buffer_sz
            else:
                raise RuntimeError("Attention, check code.")

            return start, end

        h_start, h_end = get_start_end(win_h_off, win_h_size, data_h_size, buffer_h_size)
        w_start, w_end = get_start_end(win_w_off, win_w_size, data_w_size, buffer_w_size)

        return h_start, h_end, w_start, w_end


@dataclass
class RasterProfile:
    """Metadata profile describing raster dataset characteristics."""
    height: int
    width: int
    band_count: int
    geo_transform: list
    nodata: float | int | None
    gdal_data_type: int
    spatial_ref: osr.SpatialReference

    def __eq__(self, p: object) -> bool:
        if not isinstance(p, RasterProfile):
            return False
        return (
                self.band_count == p.band_count
                and self.geo_transform == p.geo_transform
                and self.nodata == p.nodata
                and self.gdal_data_type == p.gdal_data_type
                and self.spatial_ref.IsSame(p.spatial_ref)
        )

    @staticmethod
    def from_dataset(dataset) -> 'RasterProfile':
        """Create a RasterProfile from an open GDAL dataset."""
        nodata = None
        data_types = set()

        raster_count = dataset.RasterCount
        if raster_count == 0:
            file_list = dataset.GetFileList()
            filepath = file_list[0] if file_list else "UNKNOWN filename"
            raise RuntimeError(f"Dataset has no bands: {filepath}")

        for i in range(1, raster_count + 1):
            band = dataset.GetRasterBand(i)
            _nodata = band.GetNoDataValue()
            _type = band.DataType
            data_types.add(_type)

            if nodata is None:
                nodata = _nodata
            elif _nodata != nodata:
                file_list = dataset.GetFileList()
                filepath = file_list[0] if file_list else "UNKNOW filename"
                raise RuntimeError(f"Nodata values differ between bands in file: {filepath}")

        if len(data_types) != 1:
            file_list = dataset.GetFileList()
            filepath = file_list[0] if file_list else "UNKNOW filename"
            raise RuntimeError(f"Multiple data types found in bands of file: {filepath}")

        gdal_data_type = data_types.pop()

        wkt = dataset.GetProjection()
        spatial_ref = osr.SpatialReference()

        if wkt:
            spatial_ref.ImportFromWkt(wkt)
        else:
            spatial_ref = None

        return RasterProfile(
            height=dataset.RasterYSize,
            width=dataset.RasterXSize,
            band_count=dataset.RasterCount,
            geo_transform=dataset.GetGeoTransform(),
            nodata=nodata,
            gdal_data_type=gdal_data_type,
            spatial_ref=spatial_ref,
        )


class RasterDataset:
    """Wrapper for GDAL raster datasets with enhanced reading capabilities."""

    def __init__(self, pathname: str):
        self.gdal_dataset = gdal.Open(pathname, gdal.GA_ReadOnly)

        if self.gdal_dataset is None:
            raise RuntimeError(f"Failed to open file: {pathname}")

        self.profile: RasterProfile = RasterProfile.from_dataset(self.gdal_dataset)

        self._bounds = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def width(self):
        return self.profile.width

    @property
    def height(self):
        return self.profile.height

    @property
    def band_count(self):
        return self.profile.band_count

    @property
    def bounds(self) -> list[float]:

        if self._bounds is None:
            width = self.width
            height = self.height

            geotransform = self.profile.geo_transform

            corners = [
                (0, 0),  # LeftTop
                (width, 0),  # RightTop
                (width, height),  # RightBottom
                (0, height)  # LeftBottom
            ]

            corners_geo = []
            for x, y in corners:
                x_geo = geotransform[0] + x * geotransform[1] + y * geotransform[2]
                y_geo = geotransform[3] + x * geotransform[4] + y * geotransform[5]
                corners_geo.append((x_geo, y_geo))

            # Convert to WGS84 if projection is available
            projection = self.gdal_dataset.GetProjection()
            if projection:
                source_srs = osr.SpatialReference()
                source_srs.ImportFromWkt(projection)

                target_srs = osr.SpatialReference()
                target_srs.ImportFromEPSG(4326)  # WGS84

                transform = osr.CoordinateTransformation(source_srs, target_srs)

                corners_wgs84 = []
                for x, y in corners_geo:
                    point = transform.TransformPoint(x, y)
                    corners_wgs84.append((point[0], point[1]))  # (longitude, latitude)

                corners_geo = corners_wgs84

            # Compute bounding box
            lats = [point[0] for point in corners_geo]
            lons = [point[1] for point in corners_geo]

            self._bounds = [min(lons), min(lats), max(lons), max(lats)]

        return self._bounds

    def close(self):
        if self.gdal_dataset is not None:
            self.gdal_dataset.Close()
            self.gdal_dataset = None

    def read(self,
             window: tuple[int, int, int, int] = None,
             scale: tuple[float, float] = (1, 1),
             band_idx_list: list[int] | None = None,
             nodata_to_nan: bool = False) -> np.ndarray:

        if not isinstance(window, tuple) or len(window) != 4:
            window = 0, 0, self.height, self.width

        x_off, y_off, x_size, y_size = \
            tuple(int(_window / _scale) for _window, _scale in zip(window, scale + scale))

        buf_xsize, buf_ysize = window[-2:]

        data = self.gdal_dataset.ReadAsArray(
            xoff=x_off, yoff=y_off, xsize=x_size, ysize=y_size, buf_obj=None,
            buf_xsize=buf_xsize, buf_ysize=buf_ysize, buf_type=self.profile.gdal_data_type, band_list=band_idx_list
        )

        if nodata_to_nan is True and self.profile.nodata is not None:
            if np.issubdtype(data.dtype, np.integer):
                data = data.astype(np.float32)

            data[data == self.profile.nodata] = np.nan

        return data

    def read_as_8bit(self,
                     window: Optional[Tuple[int, int, int, int]] = None,
                     scale: Tuple[float, float] = (1, 1),
                     band_idx_list: Optional[List[int]] = None,
                     lower_percent: Optional[int] = None, 
                     upper_percent: Optional[int] = None) -> np.ndarray:
        """
        Read raster data and stretch to 8-bit (0-255).
        """
        band_array = self.read(window, scale, band_idx_list)

        min_val, max_val = self.min_max(band_array, lower_percent, upper_percent)

        if max_val - min_val == 0:
            stretched_data = np.zeros_like(band_array, dtype=np.float32)
        else:
            stretched_data = (band_array - min_val) / (max_val - min_val) * 255

        # Clip to 0-255 range
        stretched_data = np.clip(stretched_data, 0, 255)

        # Handle NaNs and infinite values
        stretched_data = np.nan_to_num(stretched_data, nan=0.0, posinf=255.0, neginf=0.0)

        # Handle nodata values
        if self.profile.nodata is not None:
            stretched_data[band_array == self.profile.nodata] = 0

        return stretched_data.astype(np.uint8)

    def zoom_levels(self, pixel_size_meters: float) -> Tuple[int, int]:
        """
        Compute min/max zoom levels for Web Mercator tiling based on pixel resolution.
        """
        # Web Mercator resolution table (meters/pixel)
        resolutions = [
            156543.0339, 78271.51695, 39135.758475, 19567.8792375, 9783.93961875,
            4891.969809375, 2445.9849046875, 1222.99245234375, 611.496226171875,
            305.7481130859375, 152.87405654296876, 76.43702827148438, 38.21851413574219,
            19.109257067871095, 9.554628533935547, 4.777314266967773, 2.3886571334838866,
            1.1943285667419433, 0.5971642833709716, 0.2985821416854858, 0.1492910708427429
        ]

        # Compute maxzoom: find the highest level where resolution <= pixel size
        maxzoom = 0
        for zoom, res in enumerate(resolutions):
            if res <= pixel_size_meters:
                maxzoom = zoom
                break

        # If pixel size is smaller than the finest resolution, use the highest level
        if pixel_size_meters < resolutions[-1]:
            maxzoom = len(resolutions) - 1

        # Compute minzoom based on geographic coverage
        bounds = self.bounds
        width_deg = bounds[2] - bounds[0]
        height_deg = bounds[3] - bounds[1]
        max_dimension_deg = max(width_deg, height_deg)

        # Each zoom level doubles the granularity (360 / 2^zoom)
        minzoom = 0
        for z in range(len(resolutions)):
            if max_dimension_deg >= 360.0 / (2 ** z):
                minzoom = z
                break
        else:
            minzoom = min(len(resolutions) - 1, 12)

        minzoom = min(minzoom, maxzoom)

        return minzoom, maxzoom

    @staticmethod
    def is_valid(filepath: str) -> bool:
        """Check if a file is a valid raster dataset."""
        if not os.path.isfile(filepath):
            return False

        try:
            with RasterDataset(filepath) as dataset:
                return dataset.profile is not None
        except RuntimeError:
            return False

    @staticmethod
    def min_max(data: np.ndarray,
                lower_percent: Optional[int] = None,
                upper_percent: Optional[int] = None) -> Tuple[float, float]:
        """
        Compute min/max values, optionally using percentiles for contrast stretching.
        """
        if isinstance(lower_percent, int) and isinstance(upper_percent, int):
            try:
                min_val = np.nanpercentile(data, lower_percent)
                max_val = np.nanpercentile(data, upper_percent)
                return float(min_val), float(max_val)
            except ValueError:
                pass

        min_val = float(np.nanmin(data))
        max_val = float(np.nanmax(data))

        return min_val, max_val
