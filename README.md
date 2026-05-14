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
pip install -e ../eo-libs/stac
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

Each tool package owns its own local registry. For example, raster tools use
the package-local decorator:

```python
from .registry import tool


@tool
class HelloTool(Tool[HelloIn, HelloOut]):
    ...
```

At startup a host asks installed tool packages to discover their modules, then
builds one registry from the shared global tool pool:

```python
from geosprite.eo.tools import ToolRegistry, builtin_tools
from geosprite.eo.tools.catalog import discover_builtin_tools as discover_catalog_tools
from geosprite.eo.tools.raster import discover_builtin_tools as discover_raster_tools

discover_catalog_tools()
discover_raster_tools()
registry = ToolRegistry()
registry.register_many(builtin_tools())
```

A host can then expose the registered tools through its own API or runtime.

Each tool package can also build its own registry:

```python
from geosprite.eo.tools.raster import build_builtin_registry

registry = build_builtin_registry()
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
eo-tools list --registry-module geosprite.eo.tools.catalog.registry
eo-tools run catalog.get_grs_systems --registry-module geosprite.eo.tools.catalog.registry --json '{}'
```

REST:

```python
from geosprite.eo.tools.runtime.adapters.rest import create_app
from geosprite.eo.tools.catalog.registry import build_builtin_registry

app = create_app(build_builtin_registry())
```

MCP stdio:

```python
from geosprite.eo.tools.runtime.adapters.mcp import run_stdio
from geosprite.eo.tools.catalog.registry import build_builtin_registry

await run_stdio(build_builtin_registry())
```

The runtime also installs smoke-test entry points:

```bash
eo-tools serve-rest --registry-module geosprite.eo.tools.catalog.registry --port 8000
eo-tools serve-mcp --registry-module geosprite.eo.tools.catalog.registry
```

CLI, REST, and MCP are sibling adapters: all depend on the tool registry and
shared execution helpers, but they do not depend on each other. That keeps the
architecture open for future batch or workflow hosts without changing the tool
contract.

## Projects

Each project owns its own `pyproject.toml` and README. The root directory is an
organizing repo, not the installable Python package.
