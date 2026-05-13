# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import os

from shapely import union_all

from ..grid import SpatialGridSystemDAO, load_geom

__all__ = ["WRS2"]


class WRS2(SpatialGridSystemDAO):
    """
    WRS-2: Landsat Path/Row grid reference system.
    """

    def get_db_file(self) -> str:
        """Get the database file path."""
        return os.path.join(os.path.dirname(__file__), "etc", "wrs2.sqlite")
    
    def get_query_sql(self) -> str:
        """Get the SQL query for tiles."""
        return (
            "SELECT path, row, AsGeoJSON(ST_Envelope(GEOMETRY)) "
            "FROM landsat_tiles "
            "WHERE ST_Intersects(ST_GeomFromTEXT(?), GEOMETRY);"
        )
    
    def process_tile_row(self, row) -> dict:
        """Process a database row into tile data."""
        path, row_num, bbox = row
        parsed_bbox = load_geom(bbox)
        if parsed_bbox and not parsed_bbox.is_empty:
            tile_name = self._tile_name(path, row_num)
            return {"key": tile_name, "bbox": parsed_bbox.bounds}
        return None

    @staticmethod
    def _tile_name(path: int | str, row: int | str) -> str:
        return f"{int(path):03d}/{int(row):03d}"

    def bounds(self, tiles: list[str], batch_size: int = 1000) -> tuple:
        cur = self.conn.cursor()
        results = []

        for i in range(0, len(tiles), batch_size):
            batch = [t for t in tiles[i:i + batch_size] if '/' in t]
            if not batch:
                continue

            # Match exact path/row pairs using the same zero-padded format as _tile_name
            placeholders = ','.join(['?'] * len(batch))
            query = (
                f"SELECT AsGeoJSON(ST_Envelope(ST_Union(GEOMETRY))) "
                f"FROM landsat_tiles "
                f"WHERE (printf('%03d', path) || '/' || printf('%03d', row)) IN ({placeholders})"
            )
            cur.execute(query, batch)
            result = cur.fetchone()
            if result and result[0]:
                results.append(load_geom(result[0]))

        if results:
            return union_all(results).bounds
        return None
