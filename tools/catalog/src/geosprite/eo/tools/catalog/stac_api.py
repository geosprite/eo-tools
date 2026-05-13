"""Generic STAC API client used for local and arbitrary STAC services."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from geosprite.eo.stac import Collection, Item, ItemCollection, collection_to_stac_dict, item_to_stac_dict


class StacApiError(RuntimeError):
    """Raised when a STAC API returns an unsuccessful response."""

    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"STAC API request failed with HTTP {status}: {message}")


class GenericStacApiClient:
    """Small STAC API client for search and transaction endpoints."""

    def __init__(self, url: str, *, token: str | None = None, timeout: float = 30.0):
        self.url = url.rstrip("/") + "/"
        self.token = token
        self.timeout = timeout

    def search(self, payload: dict[str, Any]) -> ItemCollection:
        response = self._request("POST", "search", payload)
        return ItemCollection.model_validate(response)

    def create_collection(self, collection: Collection) -> Collection:
        response = self._request("POST", "collections", collection_to_stac_dict(collection))
        return Collection.model_validate(response)

    def update_collection(self, collection: Collection) -> Collection:
        response = self._request("PUT", f"collections/{collection.id}", collection_to_stac_dict(collection))
        return Collection.model_validate(response)

    def upsert_collection(self, collection: Collection) -> Collection:
        try:
            return self.create_collection(collection)
        except StacApiError as exc:
            if exc.status != 409:
                raise
        return self.update_collection(collection)

    def create_item(self, collection_id: str, item: Item) -> Item:
        response = self._request("POST", f"collections/{collection_id}/items", item_to_stac_dict(item))
        return Item.model_validate(response)

    def update_item(self, collection_id: str, item: Item) -> Item:
        response = self._request("PUT", f"collections/{collection_id}/items/{item.id}", item_to_stac_dict(item))
        return Item.model_validate(response)

    def upsert_item(self, collection_id: str, item: Item) -> Item:
        try:
            return self.create_item(collection_id, item)
        except StacApiError as exc:
            if exc.status != 409:
                raise
        return self.update_item(collection_id, item)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(
            urljoin(self.url, path.lstrip("/")),
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise StacApiError(exc.code, message) from exc

        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


__all__ = ["GenericStacApiClient", "StacApiError"]
