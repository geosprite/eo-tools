# eo-io

I/O layer for Earth Observation Tools: URI resolution, storage clients, ingest
helpers, COG/zarr utilities. Heavy dependencies (GDAL/rasterio, s3fs, gcsfs,
adlfs) live here as optional extras so other packages stay slim.

```bash
pip install eo-io                  # eo-tools-core (fsspec + aiohttp)
pip install "eo-io[gdal]"          # + GDAL/numpy/shapely raster/vector helpers
pip install "eo-io[s3,gcs,azure]"  # + cloud filesystems
pip install "eo-io[all]"           # everything
```

Public surface (initial scaffold):

| Module | Purpose |
| --- | --- |
| `uri`   | URI parsing & resolution (`file/http/s3/gs/az/store/vsi*`) |
| `geosprite.eo.io.raster` | GDAL-backed raster dataset, reader, writer, and processing helpers |
| `geosprite.eo.io.vector` | GDAL/OGR vector helpers |
| `geosprite.eo.io.coords` | GeoTransform helper utilities |
| `store` | `StoreClient` — logical paths, signed URLs, COG translate (TODO) |

This package has no workspace package dependency in its core install.
