"""
Pytest configuration and fixtures for EO Tools Catalog API tests.

Provides:
- Custom fixtures for API configuration
- Health check setup
- Pytest hooks for reporting
"""

import pytest
import requests
from typing import Generator

DEFAULT_API_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="session")
def api_base_url():
    """Provide the base API URL from environment or default."""
    import os
    return os.getenv("EO_API_URL", DEFAULT_API_URL)


@pytest.fixture(scope="session")
def api_health(api_base_url) -> bool:
    """Check API health at session start."""
    try:
        response = requests.get(f"{api_base_url}/health", timeout=5)
        is_healthy = response.status_code == 200
        if not is_healthy:
            pytest.skip(f"API health check failed: {response.status_code}")
        return is_healthy
    except requests.exceptions.ConnectionError as e:
        pytest.skip(f"Cannot connect to API at {api_base_url}: {e}")
    except Exception as e:
        pytest.skip(f"API health check error: {e}")


@pytest.fixture
def api_session(api_base_url, api_health) -> requests.Session:
    """Provide a requests session with the API base URL."""
    session = requests.Session()
    session.base_url = api_base_url
    yield session
    session.close()


def pytest_collection_modifyitems(config, items):
    """
    Add markers to tests based on test file/class names.
    
    This allows auto-marking without explicit decorators.
    """
    for item in items:
        # Auto-mark based on class name
        if "TestMSI" in item.nodeid:
            item.add_marker(pytest.mark.msi)
        elif "TestSAR" in item.nodeid:
            item.add_marker(pytest.mark.sar)
        elif "TestMultiCollection" in item.nodeid or "TestMatch" in item.nodeid:
            item.add_marker(pytest.mark.match)
        elif "TestUtility" in item.nodeid:
            item.add_marker(pytest.mark.utility)
        
        # All integration tests
        if not item.get_closest_marker("skip"):
            item.add_marker(pytest.mark.integration)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "msi: Mark test as MSI (Multispectral Imagery) search test"
    )
    config.addinivalue_line(
        "markers",
        "sar: Mark test as SAR (Synthetic Aperture Radar) search test"
    )
    config.addinivalue_line(
        "markers",
        "match: Mark test as multi-collection matching test"
    )
    config.addinivalue_line(
        "markers",
        "utility: Mark test as utility endpoint test"
    )
    config.addinivalue_line(
        "markers",
        "integration: Mark test as integration test with real API"
    )


@pytest.fixture(autouse=True)
def print_test_info(request):
    """Print test information for debugging."""
    print(f"\n{'='*70}")
    print(f"Running: {request.node.name}")
    print(f"Module: {request.node.fspath}")
    print(f"{'='*70}")


def pytest_runtest_logreport(report):
    """Hook to add custom test report information."""
    if report.when == "call":
        if report.outcome == "failed":
            print(f"\n❌ Test failed: {report.nodeid}")
            if report.longrepr:
                print(report.longrepr)


@pytest.fixture
def sample_geometry():
    """Provide sample geometries for testing."""
    return {
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[92, 36.5], [94.2, 36.5], [94.2, 38], [92, 38], [92, 36.5]]]
        },
        "point": {
            "type": "Point",
            "coordinates": [93.1, 37.25]
        },
        "bbox": [10.0, 47.5, 11.0, 48.5]
    }


@pytest.fixture
def sample_collections():
    """Provide sample collection configurations."""
    return {
        "sentinel2": {
            "id": "sentinel-2-l2a",
            "provider": "planetarycomputer",
            "assets": ["red", "green", "blue", "nir", "swir1", "swir2"],
            "typical_tile": "44SLD"
        },
        "sentinel1": {
            "id": "sentinel-1-grd",
            "provider": "planetarycomputer",
            "assets": ["vv", "vh"],
            "typical_tile": "44SLD"
        },
        "landsat": {
            "id": "landsat-c2-l2",
            "provider": "planetarycomputer",
            "assets": ["red", "nir08", "swir16"],
            "typical_tile": "001001"  # WRS2 format
        }
    }


@pytest.fixture
def sample_date_ranges():
    """Provide sample date ranges for testing."""
    return {
        "recent": "2023-09-01/2023-09-30",
        "recent_iso": "2023-09-01T00:00:00Z/2023-09-30T23:59:59Z",
        "historical": "2021-08-20/2021-08-25",
        "long_range": "2023-01-01/2023-12-31",
    }
