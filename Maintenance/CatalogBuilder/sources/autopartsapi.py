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
        self.base_url = (
            base_url
            or os.getenv("AUTOSPEC_AUTOPARTS_API_URL")
            or DEFAULT_BASE_URL
        ).strip().rstrip("/")
        self.api_key = (api_key or os.getenv("AUTOSPEC_AUTOPARTS_API_KEY") or "").strip()
        self._country_filter_id: int | None = None

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

    @staticmethod
    def _year_from_date(value: object) -> int | None:
        match = re.match(r"(19|20)\d{2}", str(value or ""))
        return int(match.group(0)) if match else None

    def country_filter_id(self, lang_id: int = DEFAULT_LANG_ID) -> int:
        if self._country_filter_id is not None:
            return self._country_filter_id
        override = os.getenv("AUTOSPEC_AUTOPARTS_COUNTRY_FILTER_ID")
        if override:
            try:
                self._country_filter_id = int(override)
                return self._country_filter_id
            except ValueError:
                pass
        payload = self._get_json(f"countries/list-countries-by-lang-id/{lang_id}")
        rows = self._find_list(payload, ("countries", "results", "items", "data"))
        wanted = {"UNITEDSTATES", "UNITEDSTATESOFAMERICA", "USA", "US"}
        for item in rows:
            name = self._first(item, "countryName", "name", "description")
            if self._norm(name) in wanted:
                raw_id = self._first(item, "countryFilterId", "countryId", "id")
                try:
                    self._country_filter_id = int(raw_id)
                    return self._country_filter_id
                except (TypeError, ValueError):
                    continue
        raise RuntimeError("United States countryFilterId not found in AutoPartsAPI countries list")

    def ping(self) -> dict[str, object]:
        payload = self._get_json("languages/list")
        rows = self._find_list(payload, ("languages", "results", "items", "data"))
        country_filter_id = self.country_filter_id() if payload else None
        return {
            "configured": self.configured,
            "ok": bool(payload),
            "language_count": len(rows),
            "country_filter_id": country_filter_id,
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

    def _models(self, manufacturer_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> list[dict[str, object]]:
        country_filter_id = country_filter_id or self.country_filter_id(lang_id)
        payload = self._get_json(
            f"models/list/type-id/{type_id}/manufacturer-id/{manufacturer_id}/lang-id/{lang_id}/country-filter-id/{country_filter_id}"
        )
        return self._find_list(payload, ("models", "results", "items", "data"))

    def _vehicles(self, model_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> list[dict[str, object]]:
        country_filter_id = country_filter_id or self.country_filter_id(lang_id)
        payload = self._get_json(
            f"types/type-id/{type_id}/list-vehicles-types/{model_id}/lang-id/{lang_id}/country-filter-id/{country_filter_id}"
        )
        return self._find_list(payload, ("vehicles", "vehicleTypes", "types", "results", "items", "data"))

    def vehicle_candidates(self, query: CatalogVehicleQuery, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> list[dict[str, object]]:
        country_filter_id = country_filter_id or self.country_filter_id(lang_id)
        resolved = self.resolve_vehicle(query, type_id, lang_id, country_filter_id)
        if resolved.get("reason") != "matched":
            return []
        wanted_year = query.year_min
        wanted_engine = str(query.engine or "").lower()
        wanted_disp = None
        match = re.search(r"(\d+(?:\.\d+)?)\s*l", wanted_engine, flags=re.I)
        if match:
            wanted_disp = float(match.group(1))
        output: list[dict[str, object]] = []
        for model in resolved.get("model_matches", []):
            if not isinstance(model, dict):
                continue
            if wanted_year:
                y0 = self._year_from_date(model.get("modelYearFrom"))
                y1 = self._year_from_date(model.get("modelYearTo"))
                if y0 is not None and wanted_year < y0:
                    continue
                if y1 is not None and wanted_year > y1:
                    continue
            model_id_raw = self._first(model, "modelId", "id")
            try:
                model_id = int(model_id_raw)
            except (TypeError, ValueError):
                continue
            for vehicle in self._vehicles(model_id, type_id, lang_id, country_filter_id):
                row = dict(vehicle)
                row["modelId"] = model_id
                row["modelName"] = self._first(model, "modelName", "name", "model")
                text = " ".join(str(v or "") for v in row.values()).lower()
                score = 0
                if "diesel" in wanted_engine and "diesel" in text:
                    score += 3
                if "turbo" in wanted_engine and "turbo" in text:
                    score += 1
                if wanted_disp is not None:
                    numeric_values: list[float] = []
                    for key in ("ccmTech", "ccm", "engineCapacity", "displacement", "capacity", "cylinderCapacity"):
                        try:
                            numeric_values.append(float(row.get(key)))
                        except (TypeError, ValueError):
                            pass
                    if any(abs(value / 1000.0 - wanted_disp) <= 0.15 for value in numeric_values if value > 100):
                        score += 4
                    if re.search(rf"\b{re.escape(str(wanted_disp))}\s*l\b", text):
                        score += 4
                row["matchScore"] = score
                output.append(row)
        return sorted(output, key=lambda item: int(item.get("matchScore") or 0), reverse=True)

    def categories_for_vehicle(self, vehicle_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID) -> list[dict[str, object]]:
        payload = self._get_json(f"category/type-id/{type_id}/products-groups-variant-4/{vehicle_id}/lang-id/{lang_id}")
        return self._find_list(payload, ("categories", "productGroups", "results", "items", "data"))

    def _matching_category_ids(self, vehicle_id: int, category: str, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID) -> list[int]:
        terms = _CATEGORY_TERMS.get(str(category or "").strip().lower(), ())
        ids: list[int] = []
        for item in self.categories_for_vehicle(vehicle_id, type_id, lang_id):
            name = str(self._first(item, "categoryName", "productGroupName", "name", "description") or "").upper()
            if not any(term in name for term in terms):
                continue
            raw_id = self._first(item, "categoryId", "productGroupId", "id")
            try:
                ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        return list(dict.fromkeys(ids))

    def _articles(self, vehicle_id: int, category_id: int, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID) -> list[dict[str, object]]:
        payload = self._get_json(f"articles/list/type-id/{type_id}/vehicle-id/{vehicle_id}/category-id/{category_id}/lang-id/{lang_id}")
        return self._find_list(payload, ("articles", "results", "items", "data"))

    def resolve_vehicle(self, query: CatalogVehicleQuery, type_id: int = DEFAULT_TYPE_ID, lang_id: int = DEFAULT_LANG_ID, country_filter_id: int | None = None) -> dict[str, object]:
        country_filter_id = country_filter_id or self.country_filter_id(lang_id)
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
            "country_filter_id": country_filter_id,
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
        if not self.configured:
            return []
        vehicles = self.vehicle_candidates(query)
        if not vehicles:
            return []
        best_score = int(vehicles[0].get("matchScore") or 0)
        if best_score <= 0:
            return []
        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str]] = set()
        for vehicle in vehicles:
            if int(vehicle.get("matchScore") or 0) != best_score:
                break
            vehicle_id_raw = self._first(vehicle, "vehicleId", "carId", "id", "typeId")
            try:
                vehicle_id = int(vehicle_id_raw)
            except (TypeError, ValueError):
                continue
            for category_id in self._matching_category_ids(vehicle_id, category):
                for item in self._articles(vehicle_id, category_id):
                    brand = str(self._first(item, "supplierName", "brandName", "manufacturerName", "brand") or "").strip()
                    part_number = str(self._first(item, "articleNo", "articleNumber", "partNumber", "part_number") or "").strip()
                    if not brand or not part_number:
                        continue
                    key = (brand.upper(), part_number.upper())
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(CatalogPartCandidate(
                        category=str(category or "").strip().lower(),
                        brand=brand,
                        part_number=part_number,
                        source=self.name,
                        confidence=0.55,
                        metadata={
                            "discovery_only": True,
                            "trusted_evidence": False,
                            "vehicle_id": vehicle_id,
                            "category_id": category_id,
                            "match_score": best_score,
                            "vehicle": vehicle,
                            "raw": item,
                        },
                    ))
        return candidates
