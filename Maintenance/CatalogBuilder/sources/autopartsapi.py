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
DEFAULT_TYPE_ID = 1
US_COUNTRY_NAMES = {"UNITED STATES", "UNITED STATES OF AMERICA", "USA", "US"}

_CATEGORY_TERMS = {
    "engine_air_filter": ("AIR FILTER", "ENGINE AIR FILTER"),
    "cabin_air_filter": ("CABIN FILTER", "POLLEN FILTER", "INTERIOR AIR FILTER"),
    "oil_filter": ("OIL FILTER",),
    "spark_plug": ("SPARK PLUG",),
    "serpentine_belt": ("V-RIBBED BELT", "SERPENTINE BELT"),
    "wheel_bearing": ("WHEEL BEARING", "WHEEL HUB"),
    "brake_pad": ("BRAKE PAD", "BRAKE PAD SET"),
}


class AutoPartsApiCandidateSource:
    name = "autopartsapi"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("AUTOSPEC_AUTOPARTS_API_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
        self.api_key = (api_key or os.getenv("AUTOSPEC_AUTOPARTS_API_KEY") or "").strip()
        self._country_filter_id: int | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _get_json(self, path: str, params: dict[str, object] | None = None) -> object:
        if not self.configured:
            return {}
        url = f"{self.base_url}/{path.lstrip('/')}"
        clean_params = {str(k): str(v) for k, v in (params or {}).items() if v not in (None, "")}
        if clean_params:
            url += "?" + urllib.parse.urlencode(clean_params)
        req = urllib.request.Request(url, headers={"Accept": "application/json", "x-apiprofile-key": self.api_key, "User-Agent": "AutoSpecCatalogBuilder/1.0"})
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

    @staticmethod
    def _year_from_date(value: object) -> int | None:
        match = re.match(r"(19|20)\d{2}", str(value or ""))
        return int(match.group(0)) if match else None

    def country_filter_id(self) -> int:
        if self._country_filter_id is not None:
            return self._country_filter_id
        payload = self._get_json("countries/list")
        rows = self._find_list(payload, ("countries", "results", "items", "data"))
        for item in rows:
            name = str(self._first(item, "countryName", "name", "country") or "").strip().upper()
            if name in US_COUNTRY_NAMES:
                raw = self._first(item, "countryFilterId", "countryId", "id")
                try:
                    self._country_filter_id = int(raw)
                    return self._country_filter_id
                except (TypeError, ValueError):
                    pass
        raise RuntimeError("United States countryFilterId not found")

    def ping(self) -> dict[str, object]:
        payload = self._get_json("languages/list")
        rows = self._find_list(payload, ("languages", "results", "items", "data"))
        return {"configured": self.configured, "ok": bool(payload), "language_count": len(rows), "country_filter_id": self.country_filter_id(), "base_url": self.base_url}

    def _manufacturer(self, make: str, type_id: int = DEFAULT_TYPE_ID) -> dict[str, object] | None:
        payload = self._get_json(f"manufacturers/list/type-id/{type_id}")
        rows = self._find_list(payload, ("manufacturers", "manufactures", "results", "items", "data"))
        wanted = self._norm(make)
        for item in rows:
            if self._norm(self._first(item, "manuName", "manufacturerName", "name", "brand")) == wanted:
                return item
        return None

    def _models(self, manufacturer_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> list[dict[str, object]]:
        cid = country_filter_id if country_filter_id is not None else self.country_filter_id()
        payload = self._get_json(f"models/list/type-id/{type_id}/manufacturer-id/{manufacturer_id}/lang-id/{lang_id}/country-filter-id/{cid}")
        return self._find_list(payload, ("models", "results", "items", "data"))

    def _vehicle_ids(self, model_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> list[dict[str, object]]:
        cid = country_filter_id if country_filter_id is not None else self.country_filter_id()
        payload = self._get_json(f"types/type-id/{type_id}/list-vehicles-id/{model_id}/lang-id/{lang_id}/country-filter-id/{cid}")
        return self._find_list(payload, ("vehicles", "vehicleTypes", "types", "results", "items", "data"))

    def _vehicle_types(self, model_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> list[dict[str, object]]:
        cid = country_filter_id if country_filter_id is not None else self.country_filter_id()
        payload = self._get_json(f"types/type-id/{type_id}/list-vehicles-types/{model_id}/lang-id/{lang_id}/country-filter-id/{cid}")
        return self._find_list(payload, ("vehicles", "vehicleTypes", "types", "results", "items", "data"))

    def probe_model_variants(self, model_id: int) -> dict[str, object]:
        return {"model_id": model_id, "country_filter_id": self.country_filter_id(), "vehicle_ids": self._vehicle_ids(model_id), "vehicle_types": self._vehicle_types(model_id)}

    def resolve_vehicle(self, query: CatalogVehicleQuery, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> dict[str, object]:
        cid = country_filter_id if country_filter_id is not None else self.country_filter_id()
        manufacturer = self._manufacturer(query.make, type_id=type_id)
        if not manufacturer:
            return {"reason": "manufacturer_not_found"}
        raw_id = self._first(manufacturer, "manuId", "manufacturerId", "id")
        try:
            manufacturer_id = int(raw_id)
        except (TypeError, ValueError):
            return {"reason": "manufacturer_id_missing", "manufacturer": manufacturer}
        wanted_model = self._norm(query.model)
        model_matches = []
        for item in self._models(manufacturer_id, type_id, lang_id, cid):
            normalized = self._norm(self._first(item, "modelName", "name", "model"))
            if normalized == wanted_model or (wanted_model and wanted_model in normalized):
                model_matches.append(item)
        return {"reason": "matched" if model_matches else "model_not_found", "manufacturer_id": manufacturer_id, "manufacturer": manufacturer, "country_filter_id": cid, "model_matches": model_matches, "query": {"make": query.make, "model": query.model, "year_min": query.year_min, "year_max": query.year_max, "engine": query.engine}}

    def vehicle_candidates(self, query: CatalogVehicleQuery) -> list[dict[str, object]]:
        resolved = self.resolve_vehicle(query)
        if resolved.get("reason") != "matched":
            return []
        year = query.year_min
        output: list[dict[str, object]] = []
        for model in resolved.get("model_matches", []):
            if not isinstance(model, dict):
                continue
            if year:
                y0 = self._year_from_date(model.get("modelYearFrom")); y1 = self._year_from_date(model.get("modelYearTo"))
                if y0 is not None and year < y0: continue
                if y1 is not None and year > y1: continue
            model_id = int(self._first(model, "modelId", "id"))
            rows = self._vehicle_types(model_id)
            if not rows:
                rows = self._vehicle_ids(model_id)
            for row in rows:
                item = dict(row); item["modelId"] = model_id; item["modelName"] = self._first(model, "modelName", "name", "model"); output.append(item)
        return output

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        return []
