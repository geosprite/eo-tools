# GeoSprite Earth Observation Tools (Core)

Core protocol package for Earth Observation (EO) Tools.

It provides the shared building blocks used by every tool package:

- `Tool`
- `ToolContext`
- `ToolRegistry`
- package-local discovery helpers

### Distribution package:
    eo-tools-core

### Import namespace:
    geosprite.eo.tools

### Description
Install this package anywhere you need to define or register EO tools
without pulling in concrete processing dependencies such as GDAL, SNAP, or STAC
clients, and without pulling in runtime dependencies such as FastAPI or MCP.

```python
from geosprite.eo.tools import Tool, ToolContext, ToolRegistry
```
