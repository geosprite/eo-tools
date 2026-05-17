# EO Tools Catalog REST API - Test Suite

This directory contains comprehensive test suites for the EO Tools Catalog REST API.

## Overview

The test suite covers three main API functionalities based on the provided examples:

1. **MSI (Multispectral Imagery) Search** - Search for satellite imagery like Sentinel-2 L2A
2. **SAR (Synthetic Aperture Radar) Search** - Search for SAR data like Sentinel-1 GRD  
3. **Multi-Collection Matching** - Search and match scenes across multiple collections
4. **Utility Endpoints** - Grid system operations (MGRS, WRS2), asset listing, bounds calculation

## Test Files

### 1. `test_catalog_api_simple.py` (Recommended for quick testing)
A standalone test script that requires only `requests` library. No pytest needed.

**Features:**
- User-friendly colored output
- Self-contained with no external test framework
- Provides detailed pass/fail information for each operation
- Easy to run and debug

**Usage:**
```bash
python test_catalog_api_simple.py
```

**Output:**
```
✓ PASS: MSI Search - Response structure
✓ PASS: MSI Search - Features contain assets
✓ PASS: MSI Search - HTTP Status
```

### 2. `test_catalog_api.py` (Pytest format)
A pytest-compatible test suite with class-based organization. Good for CI/CD integration.

**Features:**
- Standard pytest conventions
- Organized into test classes
- Can be integrated with CI/CD pipelines
- Suitable for test discovery and reporting

**Usage:**
```bash
pip install pytest requests
pytest test_catalog_api.py -v
```

### 3. `test_catalog_api_pytest.py` (Advanced pytest suite)
A comprehensive pytest suite with advanced features including parameterized tests and fixtures.

**Features:**
- Parameterized tests for multiple scenarios
- Custom fixtures for configuration
- Test markers for selective test execution
- Extended test coverage
- Better error handling and debugging

**Usage:**
```bash
# Install dependencies
pip install -r test_requirements.txt

# Run all tests
pytest test_catalog_api_pytest.py -v

# Run only MSI tests
pytest test_catalog_api_pytest.py -v -m msi

# Run only utility endpoint tests
pytest test_catalog_api_pytest.py -v -m utility

# Run with detailed output
pytest test_catalog_api_pytest.py -vv --tb=long

# Run specific test
pytest test_catalog_api_pytest.py::TestMSISearch::test_sentinel2_with_tile_and_assets -v
```

## Test Examples

### Example 1: MSI Search (Sentinel-2 L2A)
```python
payload = {
    "collection": "sentinel-2-l2a",
    "tile": "44SLD",
    "asset": ["red", "nir"],
    "datetime": "2023-09-01T00:00:00Z/2023-10-31T23:59:59Z",
    "cloud_cover": "10",
    "nodata_percent": "10",
    "sort_by": ["-properties.datetime", "properties.eo:cloud_cover"]
}
```

Tests:
- ✓ Response is a valid FeatureCollection
- ✓ Features contain requested assets
- ✓ Cloud cover filtering is applied
- ✓ Results are sorted correctly

### Example 2: SAR Search (Sentinel-1 GRD)
```python
payload = {
    "collection": "sentinel-1-grd",
    "datetime": "2021-08-20T00:00:00Z/2021-08-25T23:59:59Z",
    "orbit_state": "descending",
    "geometry": "{\"type\":\"Polygon\",\"coordinates\":[...]}",
    "tile": "44SLD",
    "provider": "planetarycomputer"
}
```

Tests:
- ✓ Response is a valid FeatureCollection
- ✓ Orbit state filtering is applied
- ✓ Geometry constraints are honored

### Example 3: Multi-Collection Matching
```python
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
```

Tests:
- ✓ Response contains valid match results
- ✓ Results respect temporal matching constraints
- ✓ Spatial overlap requirements are met

## API Endpoints Tested

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/catalog/search/msi` | POST | Search MSI collections |
| `/catalog/search/sar` | POST | Search SAR collections |
| `/catalog/match` | POST | Match scenes across collections |
| `/catalog/collection/assets` | POST | List available assets |
| `/catalog/grs/tiles` | POST | Get grid tiles for geometry |
| `/catalog/grs/bounds` | POST | Get bounds for tiles |
| `/catalog/grs/systems` | POST | List grid systems |
| `/health` | GET | Check API health |

## Prerequisites

The API must be running at `http://127.0.0.1:8000`

### Install Dependencies

For quick testing (simple test only):
```bash
pip install requests
```

For full pytest suite:
```bash
pip install -r test_requirements.txt
```

Or manually:
```bash
pip install pytest requests pytest-asyncio
```

## Running Tests

### Quick Test (Recommended for first run)
```bash
python test_catalog_api_simple.py
```

### Full Pytest Suite
```bash
pytest test_catalog_api.py -v
```

### Advanced Testing
```bash
pytest test_catalog_api_pytest.py -v --tb=short
```

### With Test Categories
```bash
# MSI tests only
pytest test_catalog_api_pytest.py -m msi

# Utility tests only
pytest test_catalog_api_pytest.py -m utility

# All integration tests
pytest test_catalog_api_pytest.py -m integration
```

## Test Markers

Tests are organized with markers for selective execution:

- `@pytest.mark.msi` - Multispectral imagery tests
- `@pytest.mark.sar` - SAR data tests
- `@pytest.mark.match` - Multi-collection matching tests
- `@pytest.mark.utility` - Utility endpoint tests
- `@pytest.mark.integration` - Integration tests with real API

## Troubleshooting

### API Not Available
```
✗ Cannot connect to http://127.0.0.1:8000
   Make sure the API server is running
```

**Solution:** Start the API server
```bash
# From the eo-tools directory
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### SAR Search Returns 500 Error
The SAR search endpoint may have specific requirements or data issues. The tests handle this gracefully by skipping when the endpoint fails.

Check the API logs for more details.

### Tests Skip with "API not available"
Ensure the API is responding to health checks:
```bash
curl http://127.0.0.1:8000/health
```

Should return 200 with a health status.

## Adding New Tests

To add new tests, follow these patterns:

### Simple Script Test
```python
def test_new_feature():
    print("\n--- Test: New Feature ---")
    try:
        response = requests.post(
            f"{BASE_URL}/catalog/...",
            json=payload,
            timeout=30
        )
        success = response.status_code == 200
        print_result("New Feature", success)
        return success
    except Exception as e:
        print_result("New Feature", False, str(e))
        return False
```

### Pytest Test
```python
@pytest.mark.integration
def test_new_feature(api_config, health_check):
    """Test description."""
    payload = {...}
    
    response = requests.post(
        f"{api_config.base_url}/catalog/...",
        json=payload,
        timeout=api_config.timeout
    )
    
    assert response.status_code == 200
    data = response.json()
    # Add assertions...
```

## CI/CD Integration

For GitHub Actions or similar CI systems:

```yaml
- name: Run API Tests
  run: |
    pip install -r test_requirements.txt
    pytest test_catalog_api_pytest.py -v --tb=short --junit-xml=test-results.xml
```

## Performance Notes

- Test timeout: 30 seconds per request
- API response times vary based on data provider
- Large spatial queries may be slower
- Consider rate limiting for repeated test runs

## References

- OpenAPI Schema: `http://127.0.0.1:8000/openapi.json`
- Health Check: `http://127.0.0.1:8000/health`
- Tool List: `http://127.0.0.1:8000/`

## Support

For issues or questions about the tests:
1. Check the troubleshooting section above
2. Review test output for detailed error messages
3. Check API logs for server-side issues
4. Verify request payloads match the OpenAPI schema
