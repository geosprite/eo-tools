# eo-stac

STAC-facing data models and publishing utilities for **Earth Observation Tools**.

This package owns asset and STAC item concepts:

| Module | Types | Purpose |
| --- | --- | --- |
| `assets` | `Asset`, `AssetCollection` | Addressable raster, vector, metadata, preview, and model-output artifacts. |
| `items` | `Item`, `ItemCollection`, `Link` | Lightweight STAC Item and FeatureCollection DTOs used by services and tools. |
| `stac` | re-export module | Backward-friendly import surface for STAC item DTOs. |

Upcoming implementation modules should live here as the STAC service grows:

- `builder.py`: convert processing/model result metadata into STAC `Item`.
- `writer.py`: write `catalog.json`, `collection.json`, and item JSON files.
- `reader.py`: read static STAC directories into typed models.
- `layout.py`: define eo-tools STAC directory layout rules.
