# eo-stac

STAC-facing data models and publishing utilities for **Earth Observation Tools**.

This package owns asset and STAC item concepts:

| Module | Types | Purpose |
| --- | --- | --- |
| `assets` | `Asset` | Addressable raster, vector, metadata, preview, and model-output artifacts. |
| `items` | `Item`, `ItemCollection` | Lightweight STAC Item and FeatureCollection DTOs used by services and tools. |
| `collections` | `Collection` | Lightweight STAC Collection DTOs and collection publishing helpers. |
| `stac` | re-export module | Backward-friendly import surface for STAC item DTOs. |
| `builder` | compatibility module | Re-exports build and serialization helpers from their owning modules. |

Upcoming implementation modules should live here as the STAC service grows:

- `writer.py`: write `catalog.json`, `collection.json`, and item JSON files.
- `reader.py`: read static STAC directories into typed models.
- `layout.py`: define eo-tools STAC directory layout rules.
