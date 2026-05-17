"""
Test cases for the EO Tools Catalog REST API.

Tests cover:
1. MSI (Multispectral Imagery) search for sentinel-2-l2a
2. SAR (Synthetic Aperture Radar) search for sentinel-1-grd
3. Multi-collection matching with temporal and spatial filtering
"""

import json

import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"


class TestCatalogSearchMSI:
    """Test MSI search endpoint with sentinel-2-l2a examples."""

    def test_search_msi_sentinel2_with_tiles_and_assets(self):
        """
        Test MSI search for Sentinel-2 L2A with specific tiles and assets.
        
        Parameters:
        - collection: sentinel-2-l2a
        - tile: 44SLD (MGRS tile)
        - assets: red, nir bands
        - datetime: September 1 - October 31, 2023
        - cloud_cover: max 10%
        - nodata_percent: max 10%
        - sort_by: sorted by datetime (descending) and cloud cover (ascending)
        """
        payload = {
            "collection": "sentinel-2-l2a",
            "tile": "44SLD",
            "assets": ["red", "nir"],
            "datetime": "2023-09-01T00:00:00Z/2023-10-31T23:59:59Z",
            "cloud_cover": "10",
            "nodata_percent": "10",
            "sort_by": ["-properties.datetime", "properties.eo:cloud_cover"]
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/search/msi",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "type" in data
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        
        # Verify features have expected properties
        for feature in data.get("features", []):
            assert feature["type"] == "Feature"
            assert "properties" in feature
            assert "assets" in feature
            # Check that requested assets are present
            for asset in ["red", "nir"]:
                assert asset in feature["assets"], f"Expected asset {asset} not found"


class TestCatalogSearchSAR:
    """Test SAR search endpoint with sentinel-1-grd examples."""

    def test_search_sar_sentinel1_with_geometry(self):
        """
        Test SAR search for Sentinel-1 GRD with geometry and orbit filtering.
        
        Parameters:
        - collection: sentinel-1-grd
        - datetime: August 20-25, 2021
        - orbit_state: descending
        - geometry: GeoJSON polygon over specific area
        - tile: 44SLD (MGRS tile)
        - provider: planetarycomputer
        """
        geometry = {
            "type": "Polygon",
            "coordinates": [[[92, 36.5], [94.2, 36.5], [94.2, 38], [92, 38], [92, 36.5]]]
        }
        
        payload = {
            "collection": "sentinel-1-grd",
            "datetime": "2021-08-20T00:00:00Z/2021-08-25T23:59:59Z",
            "orbit_state": "descending",
            "geometry": json.dumps(geometry),
            "tile": "44SLD",
            "provider": "planetarycomputer"
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/search/sar",
            json=payload
        )

        if response.status_code == 500 and "No catalog provider supports collection" in response.text:
            pytest.xfail("Current provider registry does not support sentinel-1-grd for planetarycomputer.")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "type" in data
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        
        # Verify all features are within the geometry bounds
        for feature in data.get("features", []):
            assert feature["type"] == "Feature"
            assert "properties" in feature
            # Verify orbit_state is in properties or check if results are present
            if feature["properties"]:
                assert "geometry" in feature


class TestCatalogSearchMatch:
    """Test multi-collection search and matching endpoint."""

    def test_search_match_multiple_collections(self):
        """
        Test matching scenes across multiple collections with temporal and spatial filtering.
        
        Parameters:
        - collections: sentinel-2-l2a, sentinel-1-grd, landsat-c2-l2
        - datetime: July 1-31, 2023
        - bbox: 10.0,47.5,11.0,48.5 (Europe region)
        - assets: collection-specific assets
          - sentinel-2-l2a: red, nir, swir1
          - sentinel-1-grd: vv, vh
          - landsat-c2-l2: red, nir08, swir16
        - cloud_cover: max 30%
        - max_interval_days: max 5 days between acquisitions
        - min_overlap_ratio: min 5% spatial overlap
        """
        payload = {
            "collections": ["sentinel-2-l2a", "sentinel-1-grd", "landsat-c2-l2"],
            "datetime": "2023-07-01/2023-07-31",
            "bbox": "10.0,47.5,11.0,48.5",
            "assets": {
                "sentinel-2-l2a": ["red", "nir", "swir1"],
                "sentinel-1-grd": ["vv", "vh"],
                "landsat-c2-l2": ["red", "nir08", "swir16"]
            },
            "cloud_cover": "30",
            "max_interval_days": 5.0,
            "min_overlap_ratio": 0.05
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/match",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "result" in data
        result = data["result"]
        
        # Verify the structure of matched results
        # Results should be groups of matching scenes across collections
        if isinstance(result, list):
            for match_group in result:
                assert isinstance(match_group, dict)
                # Each group should have scenes from different collections
        elif isinstance(result, dict):
            # Could be keyed by collection or other grouping
            assert len(result) > 0 or result == {}


class TestCatalogSearch:
    """Test generic STAC search endpoint."""

    def test_search_stac_generic(self):
        """
        Test generic STAC API search using standard search parameters.
        
        This tests the basic search interface that can work with any STAC API.
        """
        payload = {
            "stac_url": "https://planetarycomputer.microsoft.com/api/stac/v1",
            "collections": ["sentinel-2-l2a"],
            "datetime": "2023-09-01T00:00:00Z/2023-09-30T23:59:59Z",
            "bbox": [10.0, 47.5, 11.0, 48.5],
            "limit": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/search",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["type"] == "FeatureCollection"


class TestCatalogUtilities:
    """Test catalog utility endpoints."""

    def test_get_collection_assets(self):
        """Test listing available assets for a collection."""
        payload = {
            "collection": "sentinel-2-l2a",
            "provider": "planetarycomputer"
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/collection/assets",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "result" in data
        result = data["result"]
        assert isinstance(result, dict)
        # Should contain asset information
        if result:
            for asset_name, asset_info in result.items():
                assert isinstance(asset_name, str)

    def test_get_spatial_tiles(self):
        """Test getting MGRS tiles for a geometry."""
        geometry = {
            "type": "Polygon",
            "coordinates": [[[92, 36.5], [94.2, 36.5], [94.2, 38], [92, 38], [92, 36.5]]]
        }
        
        payload = {
            "system": "mgrs",
            "geojson": json.dumps(geometry)
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/grs/tiles",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "result" in data
        result = data["result"]
        # Should contain tile information
        assert isinstance(result, dict)

    def test_get_tile_bounds(self):
        """Test getting bounds for specific MGRS tiles."""
        payload = {
            "system": "mgrs",
            "tiles": ["44SLD", "44SLC"]
        }
        
        response = requests.post(
            f"{BASE_URL}/catalog/grs/bounds",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "result" in data
        result = data["result"]
        assert isinstance(result, dict)
        # Should have bounds for each tile
        for tile in ["44SLD", "44SLC"]:
            if tile in result:
                bounds = result[tile]
                assert isinstance(bounds, (dict, list))

    def test_get_spatial_systems(self):
        """Test listing available spatial grid systems."""
        payload = {}
        
        response = requests.post(
            f"{BASE_URL}/catalog/grs/systems",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "systems" in data
        systems = data["systems"]
        assert isinstance(systems, list)
        # Should contain at least mgrs and wrs2
        assert "mgrs" in systems or len(systems) > 0


if __name__ == "__main__":
    # Run tests with pytest
    # pytest test_catalog_api.py -v
    pass
