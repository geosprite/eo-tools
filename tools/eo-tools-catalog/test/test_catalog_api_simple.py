#!/usr/bin/env python
"""
Standalone test script for EO Tools Catalog REST API.

This script tests the three main use cases without requiring pytest:
1. MSI search with specific parameters
2. SAR search with geometry filtering
3. Multi-collection matching

Usage:
    python test_catalog_api_simple.py
"""

import json
import requests
import sys
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"

def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result in a readable format."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"       {details}")


def test_msi_search_sentinel2():
    """Test 1: MSI search for Sentinel-2 L2A with red and NIR bands."""
    print("\n--- Test 1: MSI Search (Sentinel-2 L2A) ---")
    
    payload = {
        "collection": "sentinel-2-l2a",
        "tile": "44SLD",
        "assets": ["red", "nir"],
        "datetime": "2023-09-01T00:00:00Z/2023-10-31T23:59:59Z",
        "cloud_cover": "10",
        "nodata_percent": "10",
        "sort_by": ["-properties.datetime", "properties.eo:cloud_cover"]
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/catalog/search/msi",
            json=payload,
            timeout=30
        )
        
        success = response.status_code == 200
        details = f"Status: {response.status_code}"
        
        if success:
            data = response.json()
            feature_count = len(data.get("features", []))
            details += f", Features found: {feature_count}"
            
            # Check response structure
            if data.get("type") == "FeatureCollection":
                print_result("MSI Search - Response structure", True)
            else:
                print_result("MSI Search - Response structure", False, "Not a FeatureCollection")
            
            # Validate first feature if available
            if feature_count > 0:
                first = data["features"][0]
                has_assets = "assets" in first
                print_result("MSI Search - Features contain assets", has_assets)
            
        print_result("MSI Search - HTTP Status", success, details)
        return success
        
    except Exception as e:
        print_result("MSI Search", False, str(e))
        return False


def test_sar_search_sentinel1():
    """Test 2: SAR search for Sentinel-1 GRD with geometry and orbit filtering."""
    print("\n--- Test 2: SAR Search (Sentinel-1 GRD) ---")
    
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
        "provider": "element84"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/catalog/search/sar",
            json=payload,
            timeout=30
        )
        
        success = response.status_code == 200
        details = f"Status: {response.status_code}"
        
        if success:
            data = response.json()
            feature_count = len(data.get("features", []))
            details += f", Features found: {feature_count}"
            
            if data.get("type") == "FeatureCollection":
                print_result("SAR Search - Response structure", True)
            else:
                print_result("SAR Search - Response structure", False, "Not a FeatureCollection")
        
        print_result("SAR Search - HTTP Status", success, details)
        return success
        
    except Exception as e:
        print_result("SAR Search", False, str(e))
        return False


def test_multi_collection_match():
    """Test 3: Multi-collection matching (Sentinel-2, Sentinel-1, Landsat)."""
    print("\n--- Test 3: Multi-Collection Search & Match ---")
    
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
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/catalog/match",
            json=payload,
            timeout=30
        )
        
        success = response.status_code == 200
        details = f"Status: {response.status_code}"
        
        if success:
            data = response.json()
            has_result = "result" in data
            
            if has_result:
                result = data["result"]
                if isinstance(result, list):
                    details += f", Match groups found: {len(result)}"
                else:
                    details += ", Result is a dict"
                print_result("Multi-Collection Match - Result structure", True)
            else:
                print_result("Multi-Collection Match - Result structure", False, "No 'result' field")
        
        print_result("Multi-Collection Match - HTTP Status", success, details)
        return success
        
    except Exception as e:
        print_result("Multi-Collection Match", False, str(e))
        return False


def test_utility_endpoints():
    """Test utility endpoints: collection assets, tiles, bounds, systems."""
    print("\n--- Test 4: Utility Endpoints ---")
    
    all_passed = True
    
    # Test: Get collection assets
    try:
        payload = {
            "collection": "sentinel-2-l2a",
            "provider": "planetarycomputer"
        }
        response = requests.post(
            f"{BASE_URL}/catalog/collection/assets",
            json=payload,
            timeout=30
        )
        passed = response.status_code == 200 and "result" in response.json()
        print_result("Collection Assets endpoint", passed)
        all_passed = all_passed and passed
    except Exception as e:
        print_result("Collection Assets endpoint", False, str(e))
        all_passed = False
    
    # Test: Get spatial tiles
    try:
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
            json=payload,
            timeout=30
        )
        passed = response.status_code == 200 and "result" in response.json()
        print_result("Get Tiles endpoint", passed)
        all_passed = all_passed and passed
    except Exception as e:
        print_result("Get Tiles endpoint", False, str(e))
        all_passed = False
    
    # Test: Get tile bounds
    try:
        payload = {
            "system": "mgrs",
            "tiles": ["44SLD", "44SLC"]
        }
        response = requests.post(
            f"{BASE_URL}/catalog/grs/bounds",
            json=payload,
            timeout=30
        )
        passed = response.status_code == 200 and "result" in response.json()
        print_result("Get Bounds endpoint", passed)
        all_passed = all_passed and passed
    except Exception as e:
        print_result("Get Bounds endpoint", False, str(e))
        all_passed = False
    
    # Test: Get systems
    try:
        payload = {}
        response = requests.post(
            f"{BASE_URL}/catalog/grs/systems",
            json=payload,
            timeout=30
        )
        passed = response.status_code == 200 and "systems" in response.json()
        details = ""
        if passed:
            systems = response.json()["systems"]
            details = f"Available: {', '.join(systems)}"
        print_result("Get Systems endpoint", passed, details)
        all_passed = all_passed and passed
    except Exception as e:
        print_result("Get Systems endpoint", False, str(e))
        all_passed = False
    
    return all_passed


def check_api_health():
    """Check if the API is available."""
    print("Checking API availability...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is running")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to {BASE_URL}")
        print("   Make sure the API server is running at http://127.0.0.1:8000")
        return False
    except Exception as e:
        print(f"✗ Error checking API: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("EO Tools Catalog API - Test Suite")
    print("=" * 70)
    
    if not check_api_health():
        print("\n❌ Cannot proceed: API server is not available")
        sys.exit(1)
    
    results = []
    
    # Run tests
    results.append(("MSI Search", test_msi_search_sentinel2()))
    results.append(("SAR Search", test_sar_search_sentinel1()))
    results.append(("Multi-Collection Match", test_multi_collection_match()))
    results.append(("Utility Endpoints", test_utility_endpoints()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} test groups passed")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test group(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
