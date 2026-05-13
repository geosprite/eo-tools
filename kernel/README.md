# eo-tools-kernel

Core protocol package for Earth Observation Tools.

It provides the shared building blocks used by every tool package:

- `Tool`
- `ToolContext`
- `ToolRegistry`
- package-local discovery helpers

Install this package anywhere you need to define, register, or host EO tools
without pulling in concrete processing dependencies such as GDAL, SNAP, or STAC
clients.

```python
from geosprite.eo.tools import Tool, ToolContext, ToolRegistry
```
