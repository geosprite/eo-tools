# eo-tools-raster

Raster tools for Earth Observation Tools.

This package provides raster crop, mosaic, stack, information and composite
tools under `geosprite.eo.tools.raster`. It depends on `eo-tools-core` for
the shared tool protocol and registry helpers, `eo-stac` from `../eo-libs/stac`
for asset models, and `eo-io` from `../eo-libs/io` for GDAL-backed raster I/O
helpers.

When installed, the package is discovered through the `geosprite.eo.tools`
Python entry point group.
