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

_PART_PATTERNS = {
    "WIX": r"(?:WA|WL|WP|WF|WS)?\d{4,6}[A-Z]?",
    "FRAM": r"(?:CA|CF|PH|XG|TG|CH)\d{3,6}[A-Z]?",
    "PUROLATOR": r"(?:A|C|L|P)[A-Z]?\d{4,6}",
    "MANN": r"[A-Z]{1,3}\s?\d{3,6}(?:/\d)?",
    "MAHLE": r"[A-Z]{1,3}\s?\d{3,6}",
    "ACDELCO": r"[A-Z]{1,4}\d{3,6}[A-Z]?",
    "MOTORCRAFT": r"[A-Z]{1,4}-?\d{3,6}[A-Z]?",
    "MOPAR": r"\d{7,10}[A-Z]{0,2}",
    "DENSO": r"[A-Z]{0,4}\d{4,8}[A-Z]?",
    "BOSCH": r"[A-Z0-9]{4,12}",
    "K&N": r"[A-Z]{2}-?\d{3,6}",
}


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
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
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

    @staticmethod
    def _clean_part(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", value).upper()

    def _queries(self, query: CatalogVehicleQuery, term: str) -> tuple[str, ...]:
        vehicle = self._vehicle_text(query)
        return (
            f'"{vehicle}" "{term}"',
            f'{vehicle} {term} WIX FRAM Purolator',
            f'{query.year_min or ""} {query.make} {query.model} {term} part number',
        )

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        category_key = str(category or "").strip().lower()
        term = _CATEGORY_TERMS.get(category_key)
        if not term:
            return []

        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str]] = set()

        for search_text in self._queries(query, term):
            url = GOOGLE_SEARCH_URL + "?" + urllib.parse.urlencode({"q": search_text, "num": "20", "filter": "0"})
            try:
                page = self._fetch(url)
            except Exception:
                continue

            text = self._text(page)
            if not text:
                continue

            for brand in _BRANDS:
                brand_key = brand.upper().replace("&", "")
                part_pattern = _PART_PATTERNS.get(brand_key, r"[A-Z0-9][A-Z0-9-]{3,20}")
                patterns = (
                    rf"\b{re.escape(brand)}\b[^.;|]{{0,120}}?\b({part_pattern})\b",
                    rf"\b({part_pattern})\b[^.;|]{{0,80}}?\b{re.escape(brand)}\b",
                )
                for pattern in patterns:
                    for match in re.finditer(pattern, text, flags=re.I):
                        raw = match.group(1)
                        part = self._clean_part(raw)
                        if len(part) < 4:
                            continue
                        if part.isdigit() and len(part) == 4 and part.startswith("20"):
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
