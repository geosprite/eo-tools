# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
from osgeo import gdal
from osgeo.gdal import ColorTable

from .dataset import RasterProfile, SlidingWindow

CREATE_OPTIONS = [
    "COMPRESS=DEFLATE", "TILED=YES", "INTERLEAVE=BAND",
    "NUM_THREADS=ALL_CPUS", "BIGTIFF=IF_NEEDED"
]

gdal.SetConfigOption("CPL_VSIL_USE_TEMP_FILE_FOR_RANDOM_WRITE", "YES")


class DatasetWriter:
    """
    Writes raster data to a GDAL-supported file format.
    """
    GCI_RGBBands: List[int] = [int(gdal.GCI_RedBand), int(gdal.GCI_GreenBand), int(gdal.GCI_BlueBand)]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __init__(self, pathname: str, profile: RasterProfile, driver: str = "GTiff"):
        self.pathname = pathname
        self.profile = profile
        self.dataset = self.create(driver, profile, CREATE_OPTIONS)

    def create(self, driver: str, profile: RasterProfile, options: List[str]) -> gdal.Dataset:
        """Create an empty dataset with the given profile and creation options."""
        dirname = os.path.dirname(self.pathname)

        if dirname != '' and not dirname.startswith('/vsi'):
            os.makedirs(dirname, exist_ok=True)

        dataset = gdal.GetDriverByName(driver).Create(
            self.pathname, profile.width, profile.height, profile.band_count,
            profile.gdal_data_type, options
        )

        if dataset is None:
            raise RuntimeError(f"Failed to create file '{self.pathname}'.")

        if self.profile.spatial_ref is not None:
            dataset.SetProjection(self.profile.spatial_ref.ExportToWkt())
        if self.profile.geo_transform is not None:
            dataset.SetGeoTransform(tuple(self.profile.geo_transform))

        return dataset

    def write_band(self,
                   i: int,
                   data: np.ndarray,
                   color_table: Optional[ColorTable] = None,
                   gci_rgb: bool = False,
                   x_off: int = 0,
                   y_off: int = 0):
        """Write a 2D array into a single band."""
        band = self.dataset.GetRasterBand(i)

        if self.profile.nodata is not None and band.GetNoDataValue() is None:
            band.SetNoDataValue(self.profile.nodata)

        if color_table is not None and band.GetColorTable() is None:
            band.SetColorTable(color_table)
        elif gci_rgb and self.profile.band_count >= 3 and 0 <= i < len(self.GCI_RGBBands):
            band.SetColorInterpretation(self.GCI_RGBBands[i])

        band.WriteArray(data, x_off, y_off)
        band.FlushCache()

    def write(self,
              data: np.ndarray,
              window: Optional[Tuple[int, int, int, int]] = None,
              window_buffer_size: Optional[int] = None,
              color_entries: Optional[Dict] = None,
              gci_rgb: bool = False,
              overview_levels: Optional[List[int]] = None):
        """
        Write array data into the dataset, optionally stripping buffer margins first.
        """
        try:
            # Build color table from entries if provided
            if isinstance(color_entries, dict) and len(color_entries) > 0:
                color_table = gdal.ColorTable()
                for entry, color in color_entries.items():
                    if isinstance(entry, str):
                        entry = int(entry)
                    if isinstance(color, list):
                        color = tuple(color)
                    color_table.SetColorEntry(entry, color)
            else:
                color_table = None

            # Strip buffer margins from data before writing
            if isinstance(window, tuple) and len(window) == 4 and isinstance(window_buffer_size, int):
                h_start, h_end, w_start, w_end = SlidingWindow.unbuffer(
                    window, (data.shape[-2], data.shape[-1]), window_buffer_size
                )
                data = data[..., h_start:h_end, w_start:w_end]

            dim = len(data.shape)
            offset = window[:2] if isinstance(window, tuple) and len(window) >= 2 else (0, 0)

            # Write bands
            if dim > 2:
                for i, arr in enumerate(data, start=1):
                    self.write_band(i, arr, color_table, gci_rgb, *offset)
            else:
                self.write_band(1, data, color_table, gci_rgb, *offset)

            # Build overviews if requested
            if isinstance(overview_levels, list):
                resampling = "Nearest" if color_table is not None else "Average"
                self.dataset.BuildOverviews(resampling, overview_levels)

            self.dataset.FlushCache()

        except Exception as e:
            raise RuntimeError(f"Failed to write file: {self.pathname}. (Reason: {e})")

    def close(self):

        if self.dataset is not None:
            self.dataset.Close()
            self.dataset = None


def write_cog(data: np.ndarray,
              pathname: str,
              profile: RasterProfile,
              color_entries: Optional[Dict] = None,
              gci_rgb: bool = False):
    """
    Write a Cloud-Optimized GeoTIFF (COG) from array data.
    """
    temp_file = pathname + ".temp"

    try:
        with DatasetWriter(temp_file, profile) as writer:
            writer.write(data, color_entries=color_entries, gci_rgb=gci_rgb, overview_levels=[2, 4, 8, 16, 32])

        _translate_cog(temp_file, pathname, gci_rgb=gci_rgb)
    finally:
        # Always clean up temp file
        if os.path.isfile(temp_file):
            os.remove(temp_file)
        aux_file = pathname + ".aux.xml"
        if os.path.isfile(aux_file):
            os.remove(aux_file)


def _translate_cog(input_file: str, output_file: str, gci_rgb: bool = False):
    """
    Convert a GeoTIFF to Cloud-Optimized GeoTIFF (COG) format.
    Internal helper function - use write_cog() for public API.
    """
    cog_options = ["BIGTIFF=IF_NEEDED", "NUM_THREADS=ALL_CPUS"]

    dataset = gdal.Open(input_file, gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"Failed to open input file for COG translation: {input_file}")

    try:
        band_count = dataset.RasterCount

        if gci_rgb:
            # Palette image with color table
            if band_count == 1 and dataset.GetRasterBand(1).GetRasterColorTable() is not None:
                rgb_expand = "rgba"
                cog_options.extend([
                    "OVERVIEWS=IGNORE_EXISTING", "COMPRESS=DEFLATE",
                    "PREDICTOR=2", "INTERLEAVE=BAND",
                ])
            # 3-band RGB
            elif band_count == 3:
                rgb_expand = None
                cog_options.extend([
                    "OVERVIEWS=AUTO", "INTERLEAVE=PIXEL",
                    "COMPRESS=JPEG", "QUALITY=85",
                ])
            else:
                rgb_expand = None
                cog_options.extend([
                    "OVERVIEWS=IGNORE_EXISTING", "COMPRESS=DEFLATE",
                    "PREDICTOR=2", "INTERLEAVE=BAND",
                ])
        else:
            rgb_expand = None
            cog_options.extend([
                "OVERVIEWS=IGNORE_EXISTING", "COMPRESS=DEFLATE",
                "PREDICTOR=2", "INTERLEAVE=BAND",
            ])

        if rgb_expand is not None:
            options = gdal.TranslateOptions(rgbExpand=rgb_expand, format="COG", creationOptions=cog_options)
        else:
            options = gdal.TranslateOptions(format="COG", creationOptions=cog_options)

        gdal.Translate(output_file, input_file, options=options)
    finally:
        dataset.Close()
