from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from ..models import PartRef, SourceHit
from ..sources.wix import WIX_APPLICATION_URL, fetch_applications
from .base import CatalogProvider, CatalogVehicleQuery


WIX_QUICK_SEARCH_URL = "https://www2.wixfilters.com/Lookup/LUQuickSearch.aspx"
WIX_EXACT_MATCH_URL = "https://www2.wixfilters.com/Lookup/Exactmatch.aspx?PartNo={part}"


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

    @staticmethod
    def _fetch(url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 AutoSpecVerification/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20.0) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _candidate_parts(page: str) -> list[str]:
        text = html.unescape(re.sub(r"<[^>]+>", " ", page))
        return sorted(
            {
                value.upper()
                for value in re.findall(r"\b(?:WA|WL|WP|WF|WS|570|51|46|49)?[A-Z]*\d{4,6}[A-Z]*\b", text, flags=re.I)
                if 4 <= len(re.sub(r"[^A-Za-z0-9]", "", value)) <= 10
            }
        )

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        """Best-effort discovery through WIX's public quick-search endpoint.

        WIX exposes an application-oriented quick search where Model is required and
        Make/Year are optional. Results are treated only as candidate discovery; each
        candidate must still pass the part application's fitment check before it can be
        trusted by the verifier.
        """
        model = str(query.model or "").strip()
        if not model:
            return []

        params = {"Model": model}
        if query.make:
            params["Make"] = str(query.make).strip()
        if query.year_min is not None:
            params["Year"] = str(query.year_min)

        url = f"{WIX_QUICK_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        try:
            page = self._fetch(url)
        except Exception:
            return []

        candidates = self._candidate_parts(page)
        hits: list[SourceHit] = []
        for part_number in candidates:
            # Reject obvious non-filter values by requiring WIX itself to recognize
            # the number on its exact-match page before surfacing it as a candidate.
            exact_url = WIX_EXACT_MATCH_URL.format(part=urllib.parse.quote(part_number))
            try:
                exact_page = self._fetch(exact_url)
            except Exception:
                continue
            exact_text = html.unescape(re.sub(r"<[^>]+>", " ", exact_page))
            if "Wix Part Number" not in exact_text or part_number.upper() not in exact_text.upper():
                continue

            hits.append(
                SourceHit(
                    source=self.name,
                    query=PartRef(
                        brand=f"{query.make} {query.model}".strip(),
                        part_number=str(query.year_min or ""),
                    ),
                    matched_part=PartRef(brand=self.name, part_number=part_number),
                    url=url,
                    confidence=0.5,
                    notes="Candidate discovered from WIX public quick search; requires application verification.",
                    metadata={
                        "vehicle_query": {
                            "make": query.make,
                            "model": query.model,
                            "year_min": query.year_min,
                            "year_max": query.year_max,
                            "engine": query.engine,
                        },
                        "exact_match_url": exact_url,
                    },
                )
            )
        return hits
