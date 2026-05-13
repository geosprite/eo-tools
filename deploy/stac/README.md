# Local STAC API

This folder runs a local STAC API for eo-tools development.

It uses the public `stac-fastapi-pgstac` API image with a PgSTAC/PostGIS
database and enables STAC transaction endpoints so catalog tools can create or
update collections and items.

## Start

```powershell
cd deploy/stac
docker compose up -d
```

The API is exposed at:

```text
http://localhost:8082
```

## Tool Flow

1. Run a raster, SNAP, or model tool that returns `geosprite.eo.stac.Asset`.
2. Create a collection if needed with `catalog.publish_collection`.
3. Publish a result item with `catalog.publish_item`.
4. Search local or external STAC APIs with `catalog.search`.

The STAC service is intentionally deployed outside the Python packages. The
repo owns the local development compose file, while `eo-tools` remains a tool
library and STAC client/publishing layer.
