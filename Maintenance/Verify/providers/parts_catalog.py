from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .base import CatalogVehicleQuery
from .catalog import CatalogPartCandidate


class PartsCatalogBackend:
    """Structured vehicle -> parts backend using a JSON catalog endpoint.

    The endpoint is intentionally configurable so AutoSpec can use a commercial or
    internal catalog without changing verifier code. The service is expected to accept
    vehicle/category query parameters and return JSON with a `parts` list.
    """

    name = "parts_catalog"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("AUTOSPEC_PARTS_CATALOG_URL") or "").strip()
        self.api_key = (api_key or os.getenv("AUTOSPEC_PARTS_CATALOG_KEY") or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def _request_json(self, params: dict[str, str]) -> dict[str, object]:
        if not self.configured:
            return {}
        separator = "&" if "?" in self.base_url else "?"
        url = self.base_url + separator + urllib.parse.urlencode(params)
        headers = {"User-Agent": "AutoSpecVerification/1.0", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25.0) as response:
            raw = response.read().decode("utf-8", errors="replace")
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}

    def lookup_vehicle_parts(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
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

        try:
            payload = self._request_json(params)
        except Exception:
            return []

        raw_parts = payload.get("parts")
        if not isinstance(raw_parts, list):
            return []

        candidates: list[CatalogPartCandidate] = []
        for item in raw_parts:
            if not isinstance(item, dict):
                continue
            brand = str(item.get("brand") or "").strip()
            part_number = str(item.get("part_number") or item.get("partNumber") or "").strip()
            item_category = str(item.get("category") or category or "").strip().lower()
            if not brand or not part_number:
                continue
            confidence_raw = item.get("confidence", 0.8)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.8
            candidates.append(
                CatalogPartCandidate(
                    category=item_category,
                    brand=brand,
                    part_number=part_number,
                    source=str(item.get("source") or self.name),
                    confidence=max(0.0, min(1.0, confidence)),
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key not in {"category", "brand", "part_number", "partNumber", "source", "confidence"}
                    },
                )
            )
        return candidates
