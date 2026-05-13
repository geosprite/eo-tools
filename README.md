# eo-tools

Mono repo for Earth Observation Tools.

The repo is split into one lightweight kernel project and independently
installable library and tool projects:

- `kernel/`: shared `Tool`, `ToolContext`, `ToolRegistry` and discovery helpers.
- `libs/stac/`: shared STAC asset and item models published as `eo-stac`.
- `libs/io/`: shared URI and GDAL-backed I/O helpers published as `eo-io`.
- `tools/catalog/`: STAC search and spatial grid tools.
- `tools/raster/`: GDAL-backed raster crop, mosaic, stack and composite tools.
- `tools/snap/`: SNAP and Sentinel-1 preprocessing tools.

Install the kernel and shared libraries first, then the tool packages a host
needs:

```bash
pip install -e kernel
pip install -e libs/stac
pip install -e libs/io
pip install -e tools/catalog
```

## Writing a tool

```python
from pydantic import BaseModel
from geosprite.eo.tools import Tool, ToolContext


class HelloIn(BaseModel):
    name: str = "World"


class HelloOut(BaseModel):
    greeting: str


class HelloTool(Tool[HelloIn, HelloOut]):
    name = "demo.hello"
    version = "0.1.0"
    domain = "demo"
    summary = "Echo a friendly greeting."
    description = "Returns 'Hello, <name>!'. Useful as a smoke test."
    InputModel = HelloIn
    OutputModel = HelloOut

    async def run(self, ctx: ToolContext, inputs: HelloIn) -> HelloOut:
        return HelloOut(greeting=f"Hello, {inputs.name}!")
```

## Registering a tool

Each tool package owns its own local registry. For example, raster tools use
the package-local decorator:

```python
from .registry import raster_tool


@raster_tool
class HelloTool(Tool[HelloIn, HelloOut]):
    ...
```

At startup a host imports the tool packages it installed and combines the
tools it wants to expose:

```python
from geosprite.eo.tools import ToolRegistry
from geosprite.eo.tools.catalog import builtin_tools as catalog_tools
from geosprite.eo.tools.raster import builtin_tools as raster_tools

registry = ToolRegistry()
registry.register_many(catalog_tools())
registry.register_many(raster_tools())
```

A host can then expose the registered tools through its own API or runtime.

Each tool package can also build its own registry:

```python
from geosprite.eo.tools.raster import build_builtin_registry

registry = build_builtin_registry()
```

## Projects

Each project owns its own `pyproject.toml` and README. The root directory is an
organizing repo, not the installable Python package.
