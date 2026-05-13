from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type

from shapely.geometry import GeometryCollection, shape

def load_geom(geojson: str | dict) -> GeometryCollection | None:
    """Load geometry from GeoJSON string or dict."""
    if isinstance(geojson, dict) or isinstance(geojson, str):
        import json

        if isinstance(geojson, str):
            geojson = json.loads(geojson)

        if "features" in geojson:
            features: dict = geojson["features"]
            return GeometryCollection([shape(feature["geometry"]) for feature in features])
        elif "geometry" in geojson:
            return GeometryCollection([shape(geojson["geometry"])])
        elif "coordinates" in geojson and "type" in geojson:
            return GeometryCollection([shape(geojson)])
        else:
            return None


class Batch:
    """Batch processing utility for managing tile collections."""
    
    def __init__(self, batch_size: int = -1):
        self.batch_size = batch_size
        self._tiles: dict[str, object] = {}
        self._counter = 0

    def add(self, key: str, **kwargs):
        self._tiles[key] = kwargs
        self._counter = self._counter + 1

        if 0 < self.batch_size <= self._counter:
            self._counter = 0
            return True
        else:
            return False

    def reset_tiles(self):
        self._tiles = {}

    @property
    def tiles(self) -> dict[str, object]:
        return self._tiles


class SpatialGridSystem(ABC):
    """Abstract base class for spatial grid systems."""
    
    @abstractmethod
    def get_tiles(self, geom: GeometryCollection, **kwargs) -> dict:
        """Get tiles for the given geometry."""
        pass
    
    def tiles(self, geojson, **kwargs) -> dict | None:
        """Get tiles from GeoJSON geometry."""
        geom = load_geom(geojson)
        if isinstance(geom, GeometryCollection):
            return self.get_tiles(geom, **kwargs)


class SpatialGridSystemDAO(SpatialGridSystem, ABC):
    """Base class for database-backed spatial grid systems."""
    
    def __init__(self, batch: int = -1):
        import sqlite3
        
        self.db_file = self.get_db_file()
        self.conn = sqlite3.connect(self.db_file)
        self.conn.enable_load_extension(True)
        self.conn.execute('SELECT load_extension("mod_spatialite")')
        self.batch = Batch(batch_size=batch)
    
    @abstractmethod
    def get_db_file(self) -> str:
        """Get the database file path."""
        pass
    
    @abstractmethod
    def get_query_sql(self) -> str:
        """Get the SQL query for tiles."""
        pass
    
    def close(self):
        """Close database connection."""
        self.conn.close()

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass
    
    def get_tiles(self, geom: GeometryCollection, **kwargs) -> Dict:
        """Get tiles using database query."""
        cur = self.conn.cursor()
        
        for row in cur.execute(self.get_query_sql(), (geom.wkt,)).fetchall():
            tile_data = self.process_tile_row(row)
            if tile_data and self.batch.add(**tile_data):
                yield self.batch.tiles
                self.batch.reset_tiles()
        
        yield self.batch.tiles
        cur.close()
    
    @abstractmethod
    def process_tile_row(self, row) -> Optional[Dict]:
        """Process a database row into tile data."""
        pass


class SpatialGridFactory:
    """Factory class for creating and managing spatial grid systems."""

    _systems: Dict[str, Type[SpatialGridSystem]] = {}
    _instances: Dict[str, SpatialGridSystem] = {}

    @classmethod
    def register(cls, name: str, grid_class: Type[SpatialGridSystem]) -> None:
        cls._systems[name] = grid_class

    @classmethod
    def create(cls, name: str, **kwargs) -> Optional[SpatialGridSystem]:
        """Return a cached grid instance, creating it on first use.

        kwargs are only applied on first creation; pass no kwargs when reusing.
        """
        if name in cls._instances:
            return cls._instances[name]

        system_class = cls._systems.get(name)
        if system_class:
            instance = system_class(**kwargs)
            cls._instances[name] = instance
            return instance
        return None

    @classmethod
    def get_systems(cls) -> List[str]:
        return list(cls._systems.keys())


class SpatialGridService:
    """Unified spatial grid system service.
    
    This service implements the Strategy pattern by delegating operations
    to the appropriate grid system based on system name.
    """
    
    def __init__(self, name: Optional[str] = None, **kwargs):
        """Initialize spatial grid service.
        
        Args:
            name: Optional specific system name. If None, must be specified per operation
            **kwargs: Additional parameters for system creation
        """
        self._name = name
        self._system = None
        if name:
            self._system = SpatialGridFactory.create(name, **kwargs)
            if not self._system:
                raise ValueError(f"Spatial grid system '{name}' not found")
    
    def get(self, name: str = None) -> SpatialGridSystem:
        """Get appropriate system for operation.
        
        Args:
            name: Grid system name for operation
            
        Returns:
            Grid system instance
            
        Raises:
            ValueError: If no suitable system found
        """
        if self._system:
            return self._system
        
        if name:
            system = SpatialGridFactory.create(name)
            if system:
                return system
        
        raise ValueError("No suitable system found. Specify name.")
    
    def get_tiles(self, geojson, name: str = None, **kwargs):
        """Get tiles for the given geometry.
        
        Args:
            geojson: Geometry as GeoJSON string or dict
            name: Optional specific grid system name
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of tiles
        """
        system = self.get(name)
        return system.tiles(geojson, **kwargs)
    
    def get_bounds(self, tiles: List[str], name: str = None, **kwargs):
        """Get bounds for the given tiles.
        
        Args:
            tiles: List of tile identifiers
            name: Optional specific grid system name
            **kwargs: Additional parameters
            
        Returns:
            Bounding box coordinates
        """
        system = self.get(name)
        if hasattr(system, 'bounds'):
            return system.bounds(tiles, **kwargs)
        else:
            raise NotImplementedError(f"Bounds operation not supported by {type(system).__name__}")
    
    @property
    def name(self) -> Optional[str]:
        """Get current grid system name."""
        return self._name
    
    @property
    def current_system(self):
        """Get current grid system instance."""
        return self._system
