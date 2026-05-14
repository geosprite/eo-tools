# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from abc import ABC, abstractmethod
from typing import Dict, Optional


class Collection(ABC):
    """Base class for handling specific collection types."""
    
    @property
    @abstractmethod
    def prefix(self) -> str:
        """Collection prefix this handler supports."""
        pass
    
    @abstractmethod
    def create_query(self, collection: str, **kwargs):
        """Create query for this collection type."""
        pass
    
    @abstractmethod
    def parse_item(self, args: tuple):
        """Parse item for this collection type."""
        pass


class CollectionRegistry:
    """Registry for collection handlers with loose coupling."""
    
    def __init__(self):
        self.collections: Dict[str, Collection] = {}
    
    def register(self, collection: Collection):
        """Register a collection handler."""
        prefix = collection.prefix
        self.collections[prefix] = collection
    
    def find(self, collection: str) -> Optional[Collection]:
        """Find handler for collection."""
        for prefix, handler in self.collections.items():
            if collection.startswith(prefix):
                return handler
        return None
