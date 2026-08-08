from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.catalog import CatalogPartCandidate


DEFAULT_BASE_URL = "https://auto-parts-catalog.apiprofile.com/api"
DEFAULT_LANG_ID = 4
DEFAULT_COUNTRY_FILTER_ID = 63
DEFAULT_TYPE_ID = 1


class AutoPartsApiCandidateSource:
    """Discovery-only adapter for AutoPartsAPI.

    AutoPartsAPI uses a staged lookup flow: manufacturer -> model -> vehicle -> category
    -> articles. Returned candidates are discovery evidence only until downstream
    application/provider verification approves fitment.
    """

    name = "autopartsapi"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (
            base_url
            or os.getenv("AUTOSPEC_AUTOPARTS_API_URL")
            or DEFAULT_BASE_URL
        ).strip().rstrip("/")
        self.api_key = (api_key or os.getenv("AUTOSPEC_AUTOPARTS_API_KEY") or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _get_json(self, path: str, params: dict[str, object] | None = None) -> object:
        if not self.configured:
            return {}
        url = f"{self.base_url}/{path.lstrip('/')}"
        clean_params = {
            str(key): str(value)
            for key, value in (params or {}).items()
            if value not in (None, "")
        }
        if clean_params:
            url += "?" + urllib.parse.urlencode(clean_params)
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "x-apiprofile-key": self.api_key,
                "User-Agent": "AutoSpecCatalogBuilder/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=25.0) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    @staticmethod
    def _find_list(payload: object, keys: tuple[str, ...]) -> list[dict[str, object]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        for value in payload.values():
            if isinstance(value, dict):
                found = AutoPartsApiCandidateSource._find_list(value, keys)
                if found:
                    return found
        return []

    @staticmethod
    def _norm(value: object) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())

    @staticmethod
    def _first(item: dict[str, object], *keys: str) -> object:
        for key in keys:
            if item.get(key) not in (None, ""):
                return item[key]
        return None

    def ping(self) -> dict[str, object]:
        payload = self._get_json("languages/list")
        rows = self._find_list(payload, ("languages", "results", "items", "data"))
        return {
            "configured": self.configured,
            "ok": bool(payload),
            "language_count": len(rows),
            "base_url": self.base_url,
        }

    def _manufacturer(self, make: str, type_id: int = DEFAULT_TYPE_ID) -> dict[str, object] | None:
        payload = self._get_json(f"manufacturers/list/type-id/{type_id}")
        rows = self._find_list(payload, ("manufacturers", "manufactures", "results", "items", "data"))
        wanted = self._norm(make)
        for item in rows:
            name = self._first(item, "manuName", "manufacturerName", "name", "brand")
            if self._norm(name) == wanted:
                return item
        return None

    def _models(
        self,
        manufacturer_id: int,
        type_id: int = DEFAULT_TYPE_ID,
        lang_id: int = DEFAULT_LANG_ID,
        country_filter_id: int = DEFAULT_COUNTRY_FILTER_ID,
    ) -> list[dict[str, object]]:
        payload = self._get_json(
            f"models/list/type-id/{type_id}/manufacturer-id/{manufacturer_id}/lang-id/{lang_id}/country-filter-id/{country_filter_id}"
        )
        return self._find_list(payload, ("models", "results", "items", "data"))

    def resolve_vehicle(
        self,
        query: CatalogVehicleQuery,
        type_id: int = DEFAULT_TYPE_ID,
        lang_id: int = DEFAULT_LANG_ID,
        country_filter_id: int = DEFAULT_COUNTRY_FILTER_ID,
    ) -> dict[str, object]:
        manufacturer = self._manufacturer(query.make, type_id=type_id)
        if not manufacturer:
            return {"reason": "manufacturer_not_found"}

        manufacturer_id_raw = self._first(manufacturer, "manuId", "manufacturerId", "id")
        try:
            manufacturer_id = int(manufacturer_id_raw)
        except (TypeError, ValueError):
            return {"reason": "manufacturer_id_missing", "manufacturer": manufacturer}

        wanted_model = self._norm(query.model)
        model_matches: list[dict[str, object]] = []
        for item in self._models(manufacturer_id, type_id, lang_id, country_filter_id):
            name = self._first(item, "modelName", "name", "model")
            normalized = self._norm(name)
            if normalized == wanted_model or (wanted_model and wanted_model in normalized):
                model_matches.append(item)

        return {
            "reason": "matched" if model_matches else "model_not_found",
            "manufacturer_id": manufacturer_id,
            "manufacturer": manufacturer,
            "model_matches": model_matches,
            "query": {
                "make": query.make,
                "model": query.model,
                "year_min": query.year_min,
                "year_max": query.year_max,
                "engine": query.engine,
            },
        }

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        # Full vehicle/category/article traversal is enabled after the live response shape
        # is confirmed. Keep this conservative rather than guessing IDs or fitment.
        if not self.configured:
            return []
        return []
