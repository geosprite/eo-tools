# eo-tools-raster

Tool registration and orchestration package for raster capabilities.

This package depends on `eo-raster` for GDAL raster operators, on `eo-store` for
input localization, and on `eo-tools-core` for tool discovery.

## Current Tools

| Tool | Purpose |
| --- | --- |
| `raster.stack` | Stack same-extent single-band raster inputs. |
| `raster.stack_rgb` | Stack three same-extent single-band raster inputs into an 8-bit RGB raster. |
| `raster.compose` | Compose same-extent single-band raster inputs by max, min, or median. |

## IO Policy

- Raster tools run directly through `eo-raster`.
- URI `input_files` are localized by `eo-store`: with `localization_bucket`
  they become deterministic `s3://` URIs; otherwise they become temporary local
  paths.
- `output_file` must be a local or relative path. Relative paths are resolved
  under `ToolContext.workdir`.
- Legacy split fields are not accepted: use `output_file`, not `output_uri` or
  `write_back`.
- Local outputs use boolean `overwrite` as the existence policy:
  - `false` returns an existing local file immediately without reprocessing;
  - `true` regenerates the raster and overwrites the local file.
- Response `write_back` reports whether this request wrote a new output:
  `true` for generated local outputs, `false` when an existing output was
  returned.
- Direct execution rejects `s3://` outputs. Stage remote inputs or upload
  outputs outside `eo-tools-raster` when Store behavior is needed.
- `publish_catalog` is explicit and defaults to false. The current raster tools
  reject true until Catalog publication is added as a later orchestration step.
