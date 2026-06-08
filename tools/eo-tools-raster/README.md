# eo-tools-raster

Tool registration and orchestration package for raster capabilities.

This package depends on `eo-raster` for GDAL raster operators, on `eo-store` for
input localization, and on `eo-tools-core` for tool discovery.

## Current Tools

| Tool | Purpose |
| --- | --- |
| `raster.fetch` | Fetch one raster asset through `eo-store` and optionally upload it to S3/MinIO. |
| `raster.localization` | Localize one or more raster URI inputs through `eo-store` without raster processing. |
| `raster.stack` | Stack same-extent single-band raster inputs. |
| `raster.stack_rgb` | Stack three same-extent single-band raster inputs into an 8-bit RGB raster. |
| `raster.compose` | Compose same-extent single-band raster inputs by max, min, or median. |

## IO Policy

- Raster tools run directly through `eo-raster`.
- `raster.fetch` runs through `eo-store`: `source_uri` may be `http(s)://`,
  `s3://`, `file://`, or a local path resolved under the tool workdir. Use an
  `s3://` `output_file` to upload the fetched file to the Store S3 backend,
  including the MinIO server configured by `eo-infra`.
- URI `input_files` are localized by `eo-store`: with `bucket`
  they become deterministic `s3://` URIs; otherwise they become temporary local
  paths.
- `raster.localization` exposes that same localization step directly and returns
  the localized `input_files` list for downstream tools.
- `output_file` may be a local or relative path. Relative paths are resolved
  under `ToolContext.workdir`. Raster processing tools also accept `s3://`
  outputs and stage them locally before `store.put(...)`.
- `output_format` is passed to GDAL through `eo-raster` and defaults to `COG`.
  Use `GTiff` to force a regular GeoTIFF output for comparison or debugging.
  Use `JPEG_COG` for an 8-bit RGB JPEG-compressed COG, currently intended for
  `raster.stack_rgb` preview/visual products.
- Legacy split fields are not accepted: use `output_file`, not `output_uri` or
  `write_back`.
- Local outputs use boolean `overwrite` as the existence policy:
  - `false` returns an existing local file immediately without reprocessing;
  - `true` regenerates the raster and overwrites the local file.
- Response `write_back` reports whether this request wrote a new output:
  `true` for generated local outputs, `false` when an existing output was
  returned.
- Remote outputs require `ToolContext.store` with a configured S3-compatible
  backend. For local MinIO, point the Store S3 config at the `eo-infra` MinIO
  endpoint and use `s3://bucket/key.tif` as the destination.
- `publish_catalog` is explicit and defaults to false. The current raster tools
  reject true until Catalog publication is added as a later orchestration step.
