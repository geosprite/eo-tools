# eo-tools

Mono repo for Earth Observation Tools.

The repo is split into one lightweight core project, one runtime project, and
independently installable tool plugin projects:

- `eo-tools-core/`: shared `Tool`, `ToolContext`, `ToolRegistry` and discovery
  helpers, published as `eo-tools-core`.
- `eo-tools-runtime/`: CLI, FastAPI REST, and MCP runtime adapters, published as
  `eo-tools-runtime`.
- `tools/eo-tools-catalog/`: STAC search and spatial grid tools.
- `tools/eo-tools-raster/`: GDAL-backed raster crop, mosaic, stack and composite tools.
- `tools/eo-tools-snap/`: SNAP and Sentinel-1 preprocessing tools.

Reusable EO libraries live outside this repository in the sibling `../eo-libs`
mono repo. Tool plugins can depend on one or more of those distribution
packages, such as `eo-stac`, `eo-io`, and `eo-store`.

Install the core and shared libraries first, then the tool packages a host
needs:

```bash
pip install -e eo-tools-core
pip install -e eo-tools-runtime
pip install -e ../eo-libs/eo-stac
pip install -e ../eo-libs/eo-io
pip install -e tools/eo-tools-catalog
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

Tool classes use the shared decorator from `eo-tools-core`. Runtime discovery
uses each installed plugin package's `geosprite.eo.tools` entry point.

```python
from geosprite.eo.tools import tool


@tool
class HelloTool(Tool[HelloIn, HelloOut]):
    ...
```

At startup a host can discover installed tool plugin packages from Python entry
points and build one registry:

```python
from geosprite.eo.tools import build_registry_from_entry_points

registry = build_registry_from_entry_points()
```

A host can then expose the registered tools through its own API or runtime.

For development, a host can also build a registry from one package object:

```python
import geosprite.eo.tools.raster as raster_tools
from geosprite.eo.tools import build_registry_from_package

registry = build_registry_from_package(raster_tools)
```

## Runtime adapters

The runtime project exposes any `ToolRegistry` through CLI, FastAPI REST, or
MCP. Install only what a host needs:

```bash
pip install -e eo-tools-runtime
pip install -e "eo-tools-runtime[rest]"
pip install -e "eo-tools-runtime[mcp]"
```

CLI:

```bash
eo-tools list
eo-tools run catalog.get_grs_systems --json '{}'
eo-tools list --tool-package geosprite.eo.tools.catalog
```

REST:

```python
from geosprite.eo.tools.runtime.core import load_registry
from geosprite.eo.tools.runtime.adapters.rest import create_app

app = create_app(load_registry())
```

MCP stdio:

```python
from geosprite.eo.tools.runtime.core import load_registry
from geosprite.eo.tools.runtime.adapters.mcp import run_stdio

await run_stdio(load_registry())
```

The runtime also installs commands that discover installed tool plugins:

```bash
eo-tools serve-rest --port 8000
eo-tools serve-rest \
  --tool-package geosprite.eo.tools.catalog \
  --tool-package geosprite.eo.tools.raster \
  --port 8000
eo-tools serve-mcp
```

CLI, REST, and MCP are sibling adapters: all depend on the tool registry and
shared execution helpers, but they do not depend on each other. That keeps the
architecture open for future batch or workflow hosts without changing the tool
contract.

## Projects

Each project owns its own `pyproject.toml` and README. The root directory is an
organizing repo, not the installable Python package.
