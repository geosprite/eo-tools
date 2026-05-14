# Project Structure

`eo-tools` is organized as a long-lived mono repo for Earth Observation Tools.

## Layers

- `eo-tools-core/`
  Shared tool contract layer. Owns `Tool`, `ToolContext`, `ToolRegistry`, and
  discovery helpers under `geosprite.eo.tools`. Published as `eo-tools-core`.
- `eo-tools-runtime/`
  CLI, FastAPI REST, and MCP runtime adapters under
  `geosprite.eo.tools.runtime`. Published as `eo-tools-runtime`.
- `tools/eo-tools-catalog/`
  Catalog and spatial-grid tools. Depends on `eo-tools-core` and `eo-stac`.
- `tools/eo-tools-raster/`
  Raster processing tools. Depends on `eo-tools-core`, `eo-stac`, `eo-io`, and
  `eo-store`.
- `tools/eo-tools-snap/`
  SNAP preprocessing tools. Depends on `eo-tools-core`, `eo-stac`, and
  `eo-store`.
- `../eo-libs/`
  Separate sibling mono repo for reusable EO libraries such as `eo-stac`,
  `eo-io`, and `eo-store`. It is not part of the `eo-tools` tool framework.

## Dependency Rules

- `eo-tools-core` must stay lightweight and must not depend on GDAL, SNAP, STAC
  clients, storage backends, FastAPI, or MCP.
- `eo-tools-runtime` may depend on `eo-tools-core`, but runtime adapters should remain
  siblings: CLI, REST, and MCP should not depend on each other.
- `../eo-libs/*` packages can depend on domain libraries, but must not depend on
  `eo-tools-core`, `eo-tools-runtime`, or any `eo-tools-*` plugin package.
- `tools/eo-tools-*` may depend on `eo-tools-core` and packages from
  `../eo-libs`, but should not depend on each other unless there is a deliberate
  extraction step back into `../eo-libs`.

## Working Notes

- Public package names:
  `eo-tools-core`, `eo-tools-runtime`, `eo-stac`, `eo-io`, `eo-store`,
  `eo-tools-catalog`, `eo-tools-raster`, `eo-tools-snap`.
- Public Python namespaces:
  `geosprite.eo.tools`, `geosprite.eo.tools.runtime`,
  `geosprite.eo.stac`, `geosprite.eo.io`, `geosprite.eo.store`.
- Prefer extracting shared EO code into `../eo-libs/` instead of copying logic
  across tool packages.
