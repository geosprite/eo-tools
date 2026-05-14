# eo-tools-snap

SNAP tools for Earth Observation Tools.

This package provides Sentinel-1 SNAP preprocessing tools under
`geosprite.eo.tools.snap`. It depends on `eo-tools-core` for the shared tool
protocol and registry helpers, and `eo-stac` from `libs/stac` for asset
models.

```python
from geosprite.eo.tools.snap import build_builtin_registry

registry = build_builtin_registry()
```
