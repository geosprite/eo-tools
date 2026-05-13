# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from dataclasses import replace

from osgeo import gdal

from geosprite.eo.io.raster import DatasetReader, write_cog


__all__ = ["stack_images", "stack_images2rgb"]


def stack_images(input_files: list[str], output_file: str):
    reader = DatasetReader(*input_files)
    data = reader.read()

    profile = replace(reader.profile, band_count=data.shape[-3] if len(data.shape) > 2 else 1)

    write_cog(data, output_file, profile)


def stack_images2rgb(input_files: list[str], output_file: str):
    reader = DatasetReader(*input_files)
    data = reader.read_as_8bit(2, 98)

    if data.shape[0] < 3:
        raise RuntimeError("The number of data after reading input files should be at least 3")

    profile = replace(reader.profile, band_count=data.shape[0], gdal_data_type=gdal.GDT_Byte, nodata=None)

    write_cog(data, output_file, profile, gci_rgb=True)
