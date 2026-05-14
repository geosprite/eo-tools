# AGENTS

This repository is `eo-tools`, a mono repo for Earth Observation Tools.

## Mental Model

- `eo-tools-core/` defines the tool contract and registry surface.
- `../eo-libs/stac/` provides shared STAC DTOs and publishing helpers.
- `../eo-libs/io/` provides shared URI and raster/vector I/O helpers.
- `../eo-libs/store/` provides shared asset cache and publishing helpers.
- `tools/eo-tools-*` contains installable tool packages built on top of
  `eo-tools-core` and optional `../eo-libs` packages.

## Editing Guidance

- Keep `eo-tools-core/` dependency-light.
- When functionality is shared by multiple tool packages, move it into
  `../eo-libs/stac`, `../eo-libs/io`, or another `../eo-libs` package instead
  of duplicating it.
- Tool packages should expose local registries and decorators, but not add new
  cross-tool dependencies casually.
- Preserve public Python namespaces:
  `geosprite.eo.tools`, `geosprite.eo.tools.runtime`, `geosprite.eo.stac`,
  `geosprite.eo.io`, `geosprite.eo.store`.

## Common Validation

- `python -m compileall eo-tools-core eo-tools-runtime tools`
- `PYTHONPATH=eo-tools-core/src:eo-tools-runtime/src:../eo-libs/stac/src:../eo-libs/io/src:tools/eo-tools-catalog/src:tools/eo-tools-raster/src:tools/eo-tools-snap/src python -c "import geosprite.eo.stac, geosprite.eo.io, geosprite.eo.tools.catalog.registry, geosprite.eo.tools.raster.registry, geosprite.eo.tools.snap.registry"`
