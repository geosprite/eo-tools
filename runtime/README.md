# GeoSprite Earth Observation Tools (Runtime)

Runtime adapters for Earth Observation Tools.

This package depends on `eo-tools-core` and exposes registered tools through:

- CLI
- FastAPI REST
- MCP stdio

### Distribution package:
    eo-tools-runtime

### Import namespace:
    geosprite.eo.tools.runtime


### Description

Install only the runtime adapters a host needs:

```bash
pip install -e runtime
pip install -e "eo-tools-runtime[rest]"
pip install -e "eo-tools-runtime[mcp]"
```

## Package layout

```text
geosprite.eo.tools.runtime
  core/
    context.py      # Local ToolContext implementation and factories
    execution.py    # protocol-neutral validation, execution, and output helpers
    loader.py       # entry-point loading
  adapters/
    cli.py          # eo-tools list/describe/run/serve-* commands
    rest.py         # FastAPI app factory and REST runner
    mcp.py          # MCP stdio server
```

Adapters are intentionally thin. They load registries through `core.loader`,
execute tools through `core.execution`, and do not depend on each other.

## CLI

```bash
eo-tools list
eo-tools describe catalog.get_grs_systems
eo-tools run catalog.get_grs_systems --json '{}'
eo-tools list --tool-package geosprite.eo.tools.catalog
```

## REST

```python
from geosprite.eo.tools.runtime.core import load_registry
from geosprite.eo.tools.runtime.adapters.rest import create_app

app = create_app(load_registry())
```

Or run a smoke-test service:

```bash
eo-tools serve-rest --port 8000
eo-tools serve-rest \
  --tool-package geosprite.eo.tools.catalog \
  --tool-package geosprite.eo.tools.raster \
  --port 8000
```

## MCP

```python
from geosprite.eo.tools.runtime.core import load_registry
from geosprite.eo.tools.runtime.adapters.mcp import run_stdio

await run_stdio(load_registry())
```

Or run an MCP stdio server:

```bash
eo-tools serve-mcp
eo-tools serve-mcp --tool-package geosprite.eo.tools.catalog
```

REST, MCP, and CLI are sibling adapters. They share protocol-neutral execution
helpers, but do not depend on each other.
