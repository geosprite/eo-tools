# eo-tools-raster

Raster tools for Earth Observation Tools.

This package provides raster crop, mosaic, stack, information and composite
tools under `geosprite.eo.tools.raster`. It depends on `eo-tools-kernel` for
the shared tool protocol and registry helpers, `eo-stac` from `libs/stac` for
asset models, and `eo-io` from `libs/io` for GDAL-backed raster I/O helpers.

```python
from geosprite.eo.tools.raster import build_builtin_registry

registry = build_builtin_registry()
```
