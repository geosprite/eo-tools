# AGENTS

This repository is `eo-tools`, a mono repo for Earth Observation Tools.

## Mental Model

- `kernel/` defines the tool contract and registry surface.
- `libs/stac/` provides shared STAC DTOs and publishing helpers.
- `libs/io/` provides shared URI and raster/vector I/O helpers.
- `tools/` contains installable tool packages built on top of `kernel` and
  `libs`.

## Editing Guidance

- Keep `kernel/` dependency-light.
- When functionality is shared by multiple tool packages, move it into
  `libs/stac` or `libs/io` instead of duplicating it.
- Tool packages should expose local registries and decorators, but not add new
  cross-tool dependencies casually.
- Preserve public Python namespaces:
  `geosprite.eo.tools`, `geosprite.eo.stac`, `geosprite.eo.io`.

## Common Validation

- `python -m compileall kernel libs tools`
- `PYTHONPATH=kernel/src:libs/stac/src:libs/io/src:tools/catalog/src:tools/raster/src:tools/snap/src python -c "import geosprite.eo.stac, geosprite.eo.io, geosprite.eo.tools.catalog.registry, geosprite.eo.tools.raster.registry, geosprite.eo.tools.snap.registry"`
