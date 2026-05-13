import os
from typing import List, Optional

from osgeo import gdal, ogr

class VectorReader:
    """
    Reads vector datasets via GDAL/OGR with context manager support.
    """

    def __init__(self, file: str):
        self.file = file
        self.dataset: Optional[gdal.Dataset] = gdal.OpenEx(file, gdal.OF_VECTOR)

        if self.dataset is None:
            raise RuntimeError(f"Invalid vector file: {file}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def layer(self) -> ogr.Layer:
        """Get the first layer of the vector dataset, resetting the read cursor."""
        lyr = self.dataset.GetLayer()
        lyr.ResetReading()
        return lyr

    def geometries(self) -> List[ogr.Geometry]:
        """Extract all geometries from the first layer."""
        geoms = []
        vector_layer = self.layer()

        for feature in vector_layer:
            geometry = feature.GetGeometryRef()
            if geometry is None:
                continue
            geoms.append(geometry.Clone())

        return geoms

    def close(self):
        """Close the underlying GDAL dataset."""
        if self.dataset is not None:
            self.dataset.Close()
            self.dataset = None


def rasterize(input_files: List[str],
              burn_values: List[int],
              raster_profile: 'RasterProfile',
              output_file: str,
              small_value_first: bool = False):
    """
    Burn vector geometries into a raster with given burn values.
    """
    from .raster import DatasetWriter

    if len(input_files) != len(burn_values):
        raise ValueError("The number of input files must equal the number of burn values.")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    DatasetWriter(output_file, raster_profile).close()

    if len(input_files) > 1 and small_value_first:
        zipped = sorted(zip(input_files, burn_values), key=lambda x: x[1], reverse=True)
        input_files, burn_values = zip(*zipped)

    dataset = gdal.Open(output_file, gdal.GA_Update)

    try:
        for input_file, burn_value in zip(input_files, burn_values):
            with VectorReader(input_file) as vector_reader:
                gdal.RasterizeLayer(
                    dataset=dataset, bands=[1],
                    layer=vector_reader.layer(), burn_values=[burn_value]
                )
    finally:
        dataset.Close()
