from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from ..models import PartRef, SourceHit
from ..sources.wix import WIX_APPLICATION_URL, fetch_applications
from .base import CatalogProvider, CatalogVehicleQuery


WIX_VEHICLE_SEARCH_URL = "https://www2.wixfilters.com/Lookup/filterlookup.aspx"


class WixProvider(CatalogProvider):
    name = "WIX"

    def lookup_part(self, part_number: str) -> list[SourceHit]:
        query = PartRef(brand=self.name, part_number=str(part_number or "").strip())
        if not query.part_number:
            return []

        applications = fetch_applications(query.part_number)
        url = WIX_APPLICATION_URL.format(part=query.part_number)
        if not applications:
            return [
                SourceHit(
                    source=self.name,
                    query=query,
                    matched_part=None,
                    url=url,
                    confidence=0.0,
                    notes="No WIX applications returned for this part number.",
                )
            ]

        return [
            SourceHit(
                source=self.name,
                query=query,
                matched_part=query,
                url=url,
                confidence=1.0,
                notes=f"WIX catalog returned {len(applications)} applications.",
                metadata={"applications": [application.to_dict() for application in applications]},
            )
        ]

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        """Best-effort WIX vehicle discovery using the public filter lookup page.

        WIX does not expose a documented JSON API here, so this method intentionally
        returns no evidence unless an exact part number can be parsed from the public
        HTML response. A no-result response is not treated as negative fitment evidence.
        """
        params = {
            "Make": query.make,
            "Model": query.model,
            "Engine": query.engine,
        }
        if query.year_min is not None:
            params["Year"] = str(query.year_min)

        url = f"{WIX_VEHICLE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 AutoSpecVerification/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20.0) as response:
                page = response.read().decode("utf-8", errors="replace")
        except Exception:
            return []

        text = html.unescape(re.sub(r"<[^>]+>", " ", page))
        candidates = sorted(
            {
                match.upper()
                for match in re.findall(r"\b(?:WA)?\d{4,6}\b", text, flags=re.I)
            }
        )
        hits: list[SourceHit] = []
        for part_number in candidates:
            part = PartRef(brand=self.name, part_number=part_number)
            hits.append(
                SourceHit(
                    source=self.name,
                    query=PartRef(
                        brand=f"{query.make} {query.model}".strip(),
                        part_number=str(query.year_min or ""),
                    ),
                    matched_part=part,
                    url=url,
                    confidence=0.5,
                    notes="Candidate part discovered from WIX public vehicle lookup HTML; requires application verification.",
                    metadata={
                        "vehicle_query": {
                            "make": query.make,
                            "model": query.model,
                            "year_min": query.year_min,
                            "year_max": query.year_max,
                            "engine": query.engine,
                        }
                    },
                )
            )
        return hits
