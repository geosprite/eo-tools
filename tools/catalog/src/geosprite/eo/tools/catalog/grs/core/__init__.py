# Import base classes
from .grid import (
    SpatialGridFactory,
    SpatialGridSystem,
    SpatialGridSystemDAO,
    Batch,
    load_geom
)

# Import specific implementations
from .mgrs.dao import MGRS
from .wrs2.dao import WRS2
from .wgrs import WGRS

# Register all spatial grid systems
SpatialGridFactory.register("mgrs", MGRS)
SpatialGridFactory.register("wrs2", WRS2)
SpatialGridFactory.register("wgrs", WGRS)


class SpatialGrid:
    """Unified spatial grid system interface.

    This class provides a simplified interface for working with spatial grid systems.
    It acts as a facade over the underlying SpatialGridService.
    """

    def __init__(self, name: str = None, **kwargs):
        """Initialize spatial grid system.

        Args:
            name: Optional specific system name. If None, must be specified per operation
            **kwargs: Additional parameters for system creation
        """
        from .grid import SpatialGridService
        self._service = SpatialGridService(name, **kwargs)

    def get_tiles(self, geojson, name: str = None, **kwargs):
        """Get tiles for the given geometry.

        Args:
            geojson: Geometry as GeoJSON string or dict
            name: Optional specific grid system name
            **kwargs: Additional parameters

        Returns:
            Dictionary of tiles
        """
        return self._service.get_tiles(geojson, name, **kwargs)

    def get_bounds(self, tiles: list[str], name: str = None, **kwargs):
        """Get bounds for the given tiles.

        Args:
            tiles: List of tile identifiers
            name: Optional specific grid system name
            **kwargs: Additional parameters

        Returns:
            Bounding box coordinates
        """
        return self._service.get_bounds(tiles, name, **kwargs)

    @property
    def name(self) -> str | None:
        """Get current grid system name."""
        return self._service.name

    @property
    def current_system(self):
        """Get current grid system instance."""
        return self._service.current_system


__all__ = [
    # Core classes
    "SpatialGridSystem",
    "load_geom",
    # New architecture
    "SpatialGridFactory",
    "SpatialGridSystemDAO",
    "Batch",
    "SpatialGrid",
    # Specific implementations
    "MGRS",
    "WGRS",
    "WRS2"
]
