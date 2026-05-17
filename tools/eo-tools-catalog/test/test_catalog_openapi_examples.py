"""Integration tests for catalog examples from the REST OpenAPI document."""

from __future__ import annotations

import json
from typing import Any

import pytest
import requests


MSI_PAYLOAD = {
    "collection": "sentinel-2-l2a",
    "tile": "44SLD",
    "assets": ["red", "nir"],
    "datetime": "2023-09-01T00:00:00Z/2023-10-31T23:59:59Z",
    "cloud_cover": "10",
    "nodata_percent": "10",
    "sort_by": ["-properties.datetime", "properties.eo:cloud_cover"],
}

SAR_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[[92, 36.5], [94.2, 36.5], [94.2, 38], [92, 38], [92, 36.5]]],
}

SAR_PAYLOAD = {
    "collection": "sentinel-1-grd",
    "datetime": "2021-08-20T00:00:00Z/2021-08-25T23:59:59Z",
    "orbit_state": "descending",
    "geometry": json.dumps(SAR_GEOMETRY),
    "tile": "44SLD",
    "provider": "planetarycomputer",
}

MATCH_PAYLOAD = {
    "collections": ["sentinel-2-l2a", "sentinel-1-grd", "landsat-c2-l2"],
    "datetime": "2023-07-01/2023-07-31",
    "bbox": "10.0,47.5,11.0,48.5",
    "assets": {
        "sentinel-2-l2a": ["red", "nir", "swir1"],
        "sentinel-1-grd": ["vv", "vh"],
        "landsat-c2-l2": ["red", "nir08", "swir16"],
    },
    "cloud_cover": "30",
    "max_interval_days": 5.0,
    "min_overlap_ratio": 0.05,
}


def _post(api_session: requests.Session, path: str, payload: dict[str, Any]) -> requests.Response:
    return api_session.post(f"{api_session.base_url}{path}", json=payload, timeout=60)


def _assert_feature_collection(data: dict[str, Any]) -> None:
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    for feature in data["features"]:
        assert feature["type"] == "Feature"
        assert isinstance(feature.get("properties"), dict)
        assert isinstance(feature.get("assets"), dict)


def _schema(openapi: dict[str, Any], name: str) -> dict[str, Any]:
    return openapi["components"]["schemas"][name]


@pytest.fixture(scope="session")
def openapi_doc(api_base_url: str, api_health: bool) -> dict[str, Any]:
    response = requests.get(f"{api_base_url}/openapi.json", timeout=10)
    assert response.status_code == 200, response.text
    return response.json()


def test_openapi_contains_catalog_example_endpoints(openapi_doc: dict[str, Any]) -> None:
    paths = openapi_doc["paths"]

    assert "/catalog/search/msi" in paths
    assert "/catalog/search/sar" in paths
    assert "/catalog/match" in paths

    msi_schema = _schema(openapi_doc, "SearchMSIRequest")
    sar_schema = _schema(openapi_doc, "SearchSARRequest")
    match_schema = _schema(openapi_doc, "SearchMatchIn")

    assert msi_schema["properties"]["assets"]["anyOf"][0]["type"] == "array"
    assert msi_schema["additionalProperties"] is True
    assert sar_schema["properties"]["orbit_state"]["anyOf"][0]["type"] == "string"
    assert match_schema["properties"]["assets"]["anyOf"][0]["type"] == "object"


@pytest.mark.msi
@pytest.mark.integration
def test_search_msi_sentinel2_example(api_session: requests.Session) -> None:
    response = _post(api_session, "/catalog/search/msi", MSI_PAYLOAD)

    assert response.status_code == 200, response.text
    data = response.json()
    _assert_feature_collection(data)
    for feature in data["features"]:
        assert set(feature["assets"]).issubset(set(MSI_PAYLOAD["assets"]))


@pytest.mark.sar
@pytest.mark.integration
def test_search_sar_sentinel1_example(api_session: requests.Session) -> None:
    response = _post(api_session, "/catalog/search/sar", SAR_PAYLOAD)

    if response.status_code == 500 and "No catalog provider supports collection" in response.text:
        pytest.xfail("Current provider registry does not support sentinel-1-grd for planetarycomputer.")
    assert response.status_code == 200, response.text
    data = response.json()
    _assert_feature_collection(data)
    for feature in data["features"]:
        properties = feature.get("properties", {})
        orbit_state = properties.get("sat:orbit_state")
        if orbit_state is not None:
            assert orbit_state == SAR_PAYLOAD["orbit_state"]


@pytest.mark.match
@pytest.mark.integration
def test_catalog_match_multi_collection_example(api_session: requests.Session) -> None:
    response = _post(api_session, "/catalog/match", MATCH_PAYLOAD)

    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == {"result"}

    result = data["result"]
    assert result["type"] == "MultiCollectionMatchResult"
    assert result["stac_version"] == "1.0.0"
    assert result["match_count"] == len(result["matches"])
    assert set(MATCH_PAYLOAD["collections"]).issubset(set(result["summary"]))
    for collection in MATCH_PAYLOAD["collections"]:
        assert isinstance(result["summary"][collection], int)
