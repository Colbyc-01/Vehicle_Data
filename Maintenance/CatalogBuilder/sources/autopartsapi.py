from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.catalog import CatalogPartCandidate


class AutoPartsApiCandidateSource:
    """Discovery-only adapter for a structured AutoPartsAPI-compatible service.

    Returned candidates are never treated as verified fitment evidence. The adapter is
    intentionally configurable so the trial can be exercised without coupling the rest
    of CatalogBuilder to one vendor's endpoint layout.
    """

    name = "autopartsapi"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("AUTOSPEC_AUTOPARTS_API_URL") or "").strip().rstrip("/")
        self.api_key = (api_key or os.getenv("AUTOSPEC_AUTOPARTS_API_KEY") or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _get_json(self, path: str, params: dict[str, str]) -> object:
        if not self.configured:
            return {}
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Key": self.api_key,
                "User-Agent": "AutoSpecCatalogBuilder/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=25.0) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    @staticmethod
    def _rows(payload: object) -> list[dict[str, object]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("parts", "articles", "results", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                for child_key in ("parts", "articles", "results", "items"):
                    child = value.get(child_key)
                    if isinstance(child, list):
                        return [item for item in child if isinstance(item, dict)]
        return []

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        if not self.configured:
            return []

        params = {
            "make": str(query.make or "").strip(),
            "model": str(query.model or "").strip(),
            "engine": str(query.engine or "").strip(),
            "category": str(category or "").strip().lower(),
        }
        if query.year_min is not None:
            params["year"] = str(query.year_min)

        payload = self._get_json("articles", params)
        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str]] = set()
        for item in self._rows(payload):
            brand = str(item.get("brand") or item.get("manufacturer") or item.get("brandName") or "").strip()
            part_number = str(
                item.get("part_number")
                or item.get("partNumber")
                or item.get("articleNumber")
                or item.get("mpn")
                or item.get("sku")
                or ""
            ).strip()
            if not brand or not part_number:
                continue
            key = (brand.upper(), part_number.upper())
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                CatalogPartCandidate(
                    category=str(category or "").strip().lower(),
                    brand=brand,
                    part_number=part_number,
                    source=self.name,
                    confidence=0.5,
                    metadata={
                        "discovery_only": True,
                        "trusted_evidence": False,
                        "vehicle_query": {
                            "make": query.make,
                            "model": query.model,
                            "year_min": query.year_min,
                            "year_max": query.year_max,
                            "engine": query.engine,
                        },
                        "raw": item,
                    },
                )
            )
        return candidates
