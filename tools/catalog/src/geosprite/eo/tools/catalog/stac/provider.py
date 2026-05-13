# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type

from pystac import Asset

from .item import Item
from .query import Query

class Provider(ABC):
    """Base interface for all STAC providers.
    
    This interface defines the contract that all STAC providers must implement,
    ensuring consistent behavior across different data sources like Element 84,
    Microsoft Planetary Computer, etc.
    """
    
    @abstractmethod
    def get_supported_collections(self) -> List[str]:
        """Return list of supported collection prefixes.
        
        Returns:
            List of collection prefixes this provider supports.
            Example: ["sentinel-2", "sentinel-1", "landsat"]
        """
        pass
    
    @abstractmethod
    def create_query(self, collection: str, **kwargs) -> Query:
        """Create provider-specific query object.
        
        Args:
            collection: Collection name
            **kwargs: Additional query parameters
            
        Returns:
            Provider-specific Query object
        """
        pass
    
    @abstractmethod
    def parse_item(self, args: tuple) -> Item:
        """Parse STAC item into provider-specific Item object.
        
        Args:
            args: Tuple of (stac_item, assets)
            
        Returns:
            Provider-specific Item object
        """
        pass
    
    @abstractmethod
    def search(self, query: Query, **kwargs) -> List[Item]:
        """Search items using the query.
        
        Args:
            query: Query object
            **kwargs: Additional search parameters
            
        Returns:
            List of Item objects
        """
        pass
    
    @abstractmethod
    def get_item(self, collection: str, item_id: str, assets: List[str] = None) -> Item:
        """Get single item by ID.
        
        Args:
            collection: Collection name
            item_id: Item identifier
            assets: List of assets to retrieve
            
        Returns:
            Item object
        """
        pass
    
    @property
    @abstractmethod
    def endpoint_url(self) -> str:
        """STAC endpoint URL for this provider."""
        pass
    
    def get_asset_names(self, collection: str) -> Dict[str, Asset]:
        """Get available asset names for collection.

        Args:
            collection: Collection name

        Returns:
            Dictionary of asset names and metadata
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement get_asset_names()")
    
    def supports_collection(self, collection: str) -> bool:
        """Check if collection is supported by this provider.
        
        Args:
            collection: Collection name
            
        Returns:
            True if supported, False otherwise
        """
        return any(collection.startswith(prefix) for prefix in self.get_supported_collections())


class ProviderFactory:
    """Factory class for creating and managing STAC providers.
    
    This factory implements the Factory pattern to decouple provider creation
    from the rest of the application. Providers are registered with unique names
    and can be created on demand.
    """
    
    _providers: Dict[str, Type[Provider]] = {}
    _instances: Dict[str, Provider] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[Provider]) -> None:
        """Register a provider class.
        
        Args:
            name: Unique provider name
            provider_class: Provider class that implements Provider
        """
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, name: str) -> Optional[Provider]:
        """Create a provider instance by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider instance or None if not found
        """
        if name in cls._instances:
            return cls._instances[name]
            
        provider_class = cls._providers.get(name)
        if provider_class:
            instance = provider_class()
            cls._instances[name] = instance
            return instance
        return None
    
    @classmethod
    def find_provider(cls, collection: str) -> Optional[Provider]:
        """Find provider that supports the given collection.
        
        Args:
            collection: Collection name
            
        Returns:
            Provider instance or None if no provider supports the collection
        """
        for name, provider_class in cls._providers.items():
            if name not in cls._instances:
                cls._instances[name] = provider_class()
            
            provider = cls._instances[name]
            if provider.supports_collection(collection):
                return provider
        return None
    
    @classmethod
    def get_registered_providers(cls) -> List[str]:
        """Get list of registered provider names.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        cls._instances.clear()


# Import providers after registration to avoid circular imports
from .providers.aws import Element84Provider
from .providers.pc import PlanetaryComputerProvider

# Register built-in providers
ProviderFactory.register("element84", Element84Provider)
ProviderFactory.register("planetarycomputer", PlanetaryComputerProvider)

__all__ = [
    "Provider",
    "ProviderFactory", 
    "Element84Provider",
    "PlanetaryComputerProvider"
]
