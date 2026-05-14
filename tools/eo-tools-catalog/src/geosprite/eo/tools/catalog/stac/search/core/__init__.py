from typing import List, Optional

from .client import StacClient
from .collection import Collection, CollectionRegistry
from .item import Item
from .provider import Provider, ProviderFactory
from .query import Query

class Catalog:
    """STAC catalog that automatically selects appropriate provider.
    
    This catalog implements the Strategy pattern by delegating operations
    to the appropriate provider based on collection name or explicit provider selection.
    """
    
    def __init__(self, provider_name: Optional[str] = None):
        """Initialize catalog.
        
        Args:
            provider_name: Optional specific provider name. If None, provider
                          will be selected automatically based on collection.
        """
        self._provider_name = provider_name
        self._provider = None
        if provider_name:
            self._provider = ProviderFactory.create_provider(provider_name)
            if not self._provider:
                raise ValueError(f"Provider '{provider_name}' not found")
    
    def _get_provider(self, collection: str = None) -> Provider:
        """Get appropriate provider for operation.
        
        Args:
            collection: Collection name for automatic provider selection
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If no suitable provider found
        """
        if self._provider:
            return self._provider
        
        if collection:
            provider = ProviderFactory.find_provider(collection)
            if provider:
                return provider
        
        raise ValueError("No suitable provider found. Specify provider_name or collection.")
    
    def search(self, query: Query, **kwargs) -> List[Item]:
        """Search items using the query.
        
        Args:
            query: Query object
            **kwargs: Additional search parameters
            
        Returns:
            List of Item objects
        """
        provider = self._get_provider(query.collection)
        return provider.search(query, **kwargs)
    
    def get_item(self, collection: str, item_id: str, assets: List[str] = None) -> Item:
        """Get single item by ID.
        
        Args:
            collection: Collection name
            item_id: Item identifier
            assets: List of assets to retrieve
            
        Returns:
            Item object
        """
        provider = self._get_provider(collection)
        return provider.get_item(collection, item_id, assets)
    
    def get_asset_names(self, collection: str):
        """Get available asset names for collection.
        
        Args:
            collection: Collection name
            
        Returns:
            Dictionary of asset names and metadata
        """
        provider = self._get_provider(collection)
        return provider.get_asset_names(collection)
    
    def create_query(self, collection: str, **kwargs) -> Query:
        """Create provider-specific query object.

        Args:
            collection: Collection name
            **kwargs: Additional query parameters. Unknown fields (e.g. passing
                      orbit_state to an MSI collection) are silently dropped so
                      multi-collection callers can pass a shared kwargs dict.

        Returns:
            Provider-specific Query object
        """
        provider = self._get_provider(collection)
        try:
            return provider.create_query(collection, **kwargs)
        except TypeError:
            # The collection's Query dataclass doesn't accept some of the kwargs
            # (e.g. orbit_state passed to sentinel-2). Fall back to base fields only.
            import dataclasses
            base_fields = {f.name for f in dataclasses.fields(Query)} - {"collection"}
            filtered = {k: v for k, v in kwargs.items() if k in base_fields}
            return provider.create_query(collection, **filtered)
    
    def get_supported_collections(self) -> List[str]:
        """Get all supported collections from all registered providers.
        
        Returns:
            List of supported collection prefixes
        """
        collections = []
        for provider_name in ProviderFactory.get_registered_providers():
            provider = ProviderFactory.create_provider(provider_name)
            collections.extend(provider.get_supported_collections())
        return collections
    
    @property
    def provider_name(self) -> Optional[str]:
        """Get current provider name."""
        return self._provider_name
    
    @property
    def current_provider(self) -> Optional[Provider]:
        """Get current provider instance."""
        return self._provider

__all__ = [
    # Base STAC classes
    "Item",
    "Query", 
    "StacClient",
    # New modular architecture
    "Collection",
    "CollectionRegistry",
    "Provider",
    "ProviderFactory",
    "Catalog"
]
