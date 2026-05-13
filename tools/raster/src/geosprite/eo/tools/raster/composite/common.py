from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from osgeo import gdal


def gdt_type(data: NDArray) -> int:
    data_dtype = data.dtype if isinstance(data, np.ndarray) else data
    if data_dtype == np.uint8:
        return gdal.GDT_Byte
    if data_dtype == np.uint16:
        return gdal.GDT_UInt16
    if data_dtype == np.int16:
        return gdal.GDT_Int16
    if data_dtype == np.uint32:
        return gdal.GDT_UInt32
    if data_dtype == np.int32:
        return gdal.GDT_Int32
    if data_dtype == np.float32:
        return gdal.GDT_Float32
    if data_dtype == np.float64:
        return gdal.GDT_Float64
    return gdal.GDT_Unknown

