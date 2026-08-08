from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .base import CatalogVehicleQuery
from .catalog import CatalogPartCandidate, StructuredCatalogBackend


NHTSA_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"


class NhtsaVehicleBackend(StructuredCatalogBackend):
    """Structured vehicle resolver built on NHTSA vPIC.

    vPIC is useful for normalizing vehicle identity and validating year/make/model
    combinations, but it does not publish maintenance part numbers. The backend therefore
    returns no part candidates by itself; instead it exposes a normalized vehicle payload
    that discovery backends can consume without scraping manufacturer pages.
    """

    name = "nhtsa"

    @staticmethod
    def _get_json(path: str, params: dict[str, str]) -> dict[str, object]:
        query = urllib.parse.urlencode({**params, "format": "json"})
        url = f"{NHTSA_BASE_URL}/{path}?{query}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 AutoSpecVerification/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20.0) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    def resolve_vehicle(self, query: CatalogVehicleQuery) -> dict[str, object]:
        year = str(query.year_min or "").strip()
        make = str(query.make or "").strip()
        model = str(query.model or "").strip()
        if not year or not make or not model:
            return {}

        payload = self._get_json(
            "GetModelsForMakeYear/make/{make}/modelyear/{year}".format(
                make=urllib.parse.quote(make, safe=""),
                year=urllib.parse.quote(year, safe=""),
            ),
            {},
        )
        results = payload.get("Results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return {}

        wanted = model.casefold()
        for item in results:
            if not isinstance(item, dict):
                continue
            candidate_model = str(item.get("Model_Name") or "").strip()
            if candidate_model.casefold() != wanted:
                continue
            return {
                "year": int(year),
                "make": str(item.get("Make_Name") or make).strip(),
                "model": candidate_model,
                "make_id": item.get("Make_ID"),
                "model_id": item.get("Model_ID"),
                "engine": query.engine,
                "source": "NHTSA vPIC",
            }
        return {}

    def lookup_vehicle_parts(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[CatalogPartCandidate]:
        # NHTSA does not provide maintenance part numbers. Returning [] is deliberate.
        # Call resolve_vehicle() to obtain normalized structured vehicle identity.
        self.resolve_vehicle(query)
        return []
