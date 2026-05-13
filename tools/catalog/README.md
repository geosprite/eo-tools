# eo-tools-catalog

Catalog tools for Earth Observation Tools.

This package provides STAC search and spatial grid tools under
`geosprite.eo.tools.catalog`. It depends on `eo-tools-kernel` for the shared
tool protocol and registry helpers, and on `eo-stac` from `libs/stac` for the
shared STAC item and asset models.

```python
from geosprite.eo.tools.catalog import build_builtin_registry

registry = build_builtin_registry()
```
