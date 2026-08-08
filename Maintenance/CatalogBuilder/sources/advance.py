from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.catalog import CatalogPartCandidate


class AdvanceAutoCandidateSource:
    """Discovery-only adapter for a configurable Advance Auto-style catalog endpoint.

    This source is intentionally untrusted: it may discover candidate part numbers, but
    downstream manufacturer/application verification must still approve fitment before
    any canonical data is changed.
    """

    name = "advance_auto"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("AUTOSPEC_ADVANCE_CATALOG_URL") or "").strip()
        self.api_key = (api_key or os.getenv("AUTOSPEC_ADVANCE_CATALOG_KEY") or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def _request_json(self, params: dict[str, str]) -> object:
        if not self.configured:
            return {}
        separator = "&" if "?" in self.base_url else "?"
        url = self.base_url + separator + urllib.parse.urlencode(params)
        headers = {
            "Accept": "application/json",
            "User-Agent": "AutoSpecCatalogBuilder/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25.0) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    @staticmethod
    def _parts(payload: object) -> list[dict[str, object]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("parts", "products", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("parts", "products", "results", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        if not self.configured:
            return []

        params = {
            "category": str(category or "").strip(),
            "make": str(query.make or "").strip(),
            "model": str(query.model or "").strip(),
            "engine": str(query.engine or "").strip(),
        }
        if query.year_min is not None:
            params["year"] = str(query.year_min)

        payload = self._request_json(params)
        candidates: list[CatalogPartCandidate] = []
        for item in self._parts(payload):
            brand = str(item.get("brand") or item.get("manufacturer") or "").strip()
            part_number = str(
                item.get("part_number")
                or item.get("partNumber")
                or item.get("sku")
                or item.get("partNo")
                or ""
            ).strip()
            if not brand or not part_number:
                continue
            candidates.append(
                CatalogPartCandidate(
                    category=str(item.get("category") or category or "").strip().lower(),
                    brand=brand,
                    part_number=part_number,
                    source=self.name,
                    confidence=0.45,
                    metadata={
                        "discovery_only": True,
                        "trusted_evidence": False,
                        "raw": item,
                    },
                )
            )
        return candidates
