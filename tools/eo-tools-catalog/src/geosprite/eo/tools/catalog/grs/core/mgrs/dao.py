import os

from shapely import union_all

from ..grid import SpatialGridSystemDAO, load_geom

__all__ = ['MGRS']


class MGRS(SpatialGridSystemDAO):
    """
    MGRS: Military Grid Reference System. Sentinel-2 使用的格网
    """
    
    def get_db_file(self) -> str:
        """Get the database file path."""
        return os.path.join(os.path.dirname(__file__), "etc/mgrs.sqlite")
    
    def get_query_sql(self) -> str:
        """Get the SQL query for tiles."""
        return "SELECT name, AsGeoJSON(ST_Envelope(geometry)) from MGRS where ST_Intersects(ST_GeomFromTEXT(?), geometry);"
    
    def process_tile_row(self, row) -> dict:
        """Process a database row into tile data."""
        name, bbox = row
        parsed_bbox = load_geom(bbox)
        if parsed_bbox and not parsed_bbox.is_empty:
            return {"key": name, "bbox": parsed_bbox.bounds}
        return None

    def bounds(self, tiles: list[str], batch_size: int = 1000) -> tuple:
        cur = self.conn.cursor()

        results = []

        for i in range(0, len(tiles), batch_size):
            batch = tiles[i:i + batch_size]
            placeholders = ','.join(['?'] * len(batch))

            query = f"SELECT AsGeoJSON(ST_Envelope(ST_Union(geometry))) AS bbox FROM MGRS WHERE name IN ({placeholders})"
            cur.execute(query, batch)

            results.append(load_geom(cur.fetchone()[0]))

        return union_all(results).bounds
