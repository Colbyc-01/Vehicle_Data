from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.catalog import CatalogPartCandidate


GOOGLE_SEARCH_URL = "https://www.google.com/search"

_CATEGORY_TERMS = {
    "engine_air_filter": "engine air filter",
    "cabin_air_filter": "cabin air filter",
    "oil_filter": "oil filter",
    "spark_plug": "spark plug",
    "serpentine_belt": "serpentine belt",
    "wheel_bearing": "wheel bearing",
    "brake_pad": "brake pads",
}

_BRANDS = (
    "WIX",
    "FRAM",
    "Purolator",
    "MANN",
    "Mahle",
    "ACDelco",
    "Motorcraft",
    "Mopar",
    "Denso",
    "Bosch",
    "K&N",
)


class GoogleSearchCandidateSource:
    """Discovery-only fallback using public search-result text.

    Search results are not trusted fitment evidence. This source only proposes candidate
    brand/part pairs that must be verified against manufacturer application data before
    any canonical maintenance record can be changed.
    """

    name = "google_search"

    @staticmethod
    def _fetch(url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "Mozilla/5.0 AutoSpecCatalogBuilder/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=20.0) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _text(value: str) -> str:
        return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())

    @staticmethod
    def _vehicle_text(query: CatalogVehicleQuery) -> str:
        values = (
            str(query.year_min or "").strip(),
            str(query.make or "").strip(),
            str(query.model or "").strip(),
            str(query.engine or "").strip(),
        )
        return " ".join(value for value in values if value)

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        category_key = str(category or "").strip().lower()
        term = _CATEGORY_TERMS.get(category_key)
        if not term:
            return []

        search_text = f'"{self._vehicle_text(query)}" "{term}" part number'
        url = GOOGLE_SEARCH_URL + "?" + urllib.parse.urlencode({"q": search_text, "num": "20"})
        try:
            page = self._fetch(url)
        except Exception:
            return []

        text = self._text(page)
        if not text:
            return []

        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str]] = set()
        for brand in _BRANDS:
            pattern = re.compile(
                rf"\b{re.escape(brand)}\b[^.;|]{{0,100}}?\b(?:part(?:\s+number)?|p/?n|filter)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{{3,20}})\b",
                flags=re.I,
            )
            for match in pattern.finditer(text):
                part = re.sub(r"[^A-Za-z0-9]", "", match.group(1)).upper()
                if len(part) < 4 or part.isdigit() and len(part) == 4 and part.startswith("20"):
                    continue
                key = (brand.upper(), part)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    CatalogPartCandidate(
                        category=category_key,
                        brand=brand,
                        part_number=part,
                        source=self.name,
                        confidence=0.2,
                        metadata={
                            "discovery_only": True,
                            "trusted_evidence": False,
                            "search_url": url,
                            "search_text": search_text,
                        },
                    )
                )
        return candidates
