"""eo-io: storage and I/O helpers for Earth Observation Tools."""

from .uri import URI, parse_uri

try:
    from .coords import GeoTransformHelper
except ModuleNotFoundError:
    GeoTransformHelper = None

try:
    from .vector import VectorReader
except ModuleNotFoundError:
    VectorReader = None

__all__ = ["GeoTransformHelper", "URI", "VectorReader", "parse_uri"]

__version__ = "0.1.0"
