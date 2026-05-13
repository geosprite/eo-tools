# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from .window import (
    RasterWindow,
    affine_coefficients,
    aligned_geometry_boundary,
    geometry_to_window,
    gdal_to_affine,
    is_orthogonal_affine,
    pixel_to_world,
    window_to_geometry,
    world_to_pixel,
)

try:
    from .dataset import RasterDataset, RasterProfile, SlidingWindow
    from .processing import RasterInfo, crop_raster, dataset_path, normalize_resampling, raster_info
    from .reader import DatasetReader
    from .writer import DatasetWriter, write_cog
except ModuleNotFoundError:
    DatasetReader = None
    DatasetWriter = None
    RasterDataset = None
    RasterInfo = None
    RasterProfile = None
    SlidingWindow = None
    crop_raster = None
    dataset_path = None
    normalize_resampling = None
    raster_info = None
    write_cog = None

__all__ = [
    "DatasetReader",
    "DatasetWriter",
    "RasterDataset",
    "RasterProfile",
    "SlidingWindow",
    "RasterInfo",
    "RasterWindow",
    "affine_coefficients",
    "aligned_geometry_boundary",
    "crop_raster",
    "dataset_path",
    "geometry_to_window",
    "gdal_to_affine",
    "is_orthogonal_affine",
    "normalize_resampling",
    "pixel_to_world",
    "raster_info",
    "window_to_geometry",
    "world_to_pixel",
    "write_cog",
]
