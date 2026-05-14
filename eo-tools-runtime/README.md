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
pip install -e eo-tools-runtime
pip install -e "eo-tools-runtime[rest]"
pip install -e "eo-tools-runtime[mcp]"
```

## Package layout

```text
geosprite.eo.tools.runtime
  core/
    context.py      # Local ToolContext implementation and factories
    execution.py    # protocol-neutral validation, execution, and output helpers
    loader.py       # registry-module loading
  adapters/
    cli.py          # eo-tools list/describe/run/serve-* commands
    rest.py         # FastAPI app factory and REST runner
    mcp.py          # MCP stdio server
```

Adapters are intentionally thin. They load registries through `core.loader`,
execute tools through `core.execution`, and do not depend on each other.

## CLI

```bash
eo-tools list --registry-module geosprite.eo.tools.catalog.registry
eo-tools describe catalog.get_grs_systems --registry-module geosprite.eo.tools.catalog.registry
eo-tools run catalog.get_grs_systems --registry-module geosprite.eo.tools.catalog.registry --json '{}'
```

## REST

```python
from geosprite.eo.tools.runtime.adapters.rest import create_app
from geosprite.eo.tools.catalog.registry import build_builtin_registry

app = create_app(build_builtin_registry())
```

Or run a smoke-test service:

```bash
eo-tools serve-rest --registry-module geosprite.eo.tools.catalog.registry --port 8000
```

## MCP

```python
from geosprite.eo.tools.runtime.adapters.mcp import run_stdio
from geosprite.eo.tools.catalog.registry import build_builtin_registry

await run_stdio(build_builtin_registry())
```

Or run an MCP stdio server:

```bash
eo-tools serve-mcp --registry-module geosprite.eo.tools.catalog.registry
```

REST, MCP, and CLI are sibling adapters. They share protocol-neutral execution
helpers, but do not depend on each other.
