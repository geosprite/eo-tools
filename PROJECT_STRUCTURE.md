# Project Structure

`eo-tools` is organized as a long-lived mono repo for Earth Observation Tools.

## Layers

- `eo-tools-core/`
  Shared tool contract layer. Owns `Tool`, `ToolContext`, `ToolRegistry`, and
  discovery helpers under `geosprite.eo.tools`. Published as `eo-tools-core`.
- `eo-tools-runtime/`
  CLI, FastAPI REST, and MCP runtime adapters under
  `geosprite.eo.tools.runtime`. Published as `eo-tools-runtime`.
- `libs/stac/`
  Shared STAC models published as `eo-stac` under `geosprite.eo.stac`.
- `libs/io/`
  Shared I/O and GDAL compatibility helpers published as `eo-io` under
  `geosprite.eo.io`.
- `tools/catalog/`
  Catalog and spatial-grid tools. Depends on `eo-tools-core` and `libs/stac`.
- `tools/raster/`
  Raster processing tools. Depends on `eo-tools-core`, `libs/stac`, and
  `libs/io`.
- `tools/snap/`
  SNAP preprocessing tools. Depends on `eo-tools-core` and currently uses
  `libs/stac`.

## Dependency Rules

- `core` must stay lightweight and must not depend on GDAL, SNAP, STAC
  clients, storage backends, FastAPI, or MCP.
- `runtime` may depend on `core`, but runtime adapters should remain
  siblings: CLI, REST, and MCP should not depend on each other.
- `libs/*` can depend on domain libraries, but must not depend on `tools/*`.
- `tools/*` may depend on `core` and `libs/*`, but should not depend on each
  other unless there is a deliberate extraction step back into `libs/`.

## Working Notes

- Public package names:
  `eo-tools-core`, `eo-tools-runtime`, `eo-stac`, `eo-io`, `eo-tools-catalog`,
  `eo-tools-raster`, `eo-tools-snap`.
- Public Python namespaces:
  `geosprite.eo.tools`, `geosprite.eo.tools.runtime`,
  `geosprite.eo.stac`, `geosprite.eo.io`.
- Prefer extracting shared code into `libs/` instead of copying logic across
  tool packages.
