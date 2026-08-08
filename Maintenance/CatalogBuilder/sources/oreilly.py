from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.catalog import CatalogPartCandidate


OREILLY_SEARCH_URL = "https://www.oreillyauto.com/search"

_CATEGORY_TERMS = {
    "engine_air_filter": "air filter",
    "cabin_air_filter": "cabin air filter",
    "oil_filter": "oil filter",
    "spark_plug": "spark plug",
    "serpentine_belt": "serpentine belt",
    "wheel_bearing": "wheel bearing",
    "brake_pad": "brake pads",
}


class OReillyCandidateSource:
    """Discovery-only adapter for O'Reilly public search pages.

    This source is deliberately untrusted. It may surface candidate brand/part numbers,
    but downstream manufacturer/application verification must approve fitment before any
    canonical maintenance data changes.
    """

    name = "oreilly"

    @staticmethod
    def _fetch(url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "Mozilla/5.0 AutoSpecCatalogBuilder/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=25.0) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _text(value: str) -> str:
        return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())

    @staticmethod
    def _vehicle_token(query: CatalogVehicleQuery) -> str:
        year = str(query.year_min or "").strip()
        make = str(query.make or "").strip()
        model = str(query.model or "").strip()
        engine = str(query.engine or "").strip()
        return " ".join(value for value in (year, make, model, engine) if value)

    def discover(self, query: CatalogVehicleQuery, category: str) -> list[CatalogPartCandidate]:
        category_key = str(category or "").strip().lower()
        term = _CATEGORY_TERMS.get(category_key)
        if not term:
            return []

        search_text = f"{self._vehicle_token(query)} {term}".strip()
        url = OREILLY_SEARCH_URL + "?" + urllib.parse.urlencode({"q": search_text})
        try:
            page = self._fetch(url)
        except Exception:
            return []

        page_text = self._text(page)
        if not page_text:
            return []

        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str]] = set()

        # O'Reilly product pages commonly render visible Brand + Part Number text.
        # Keep extraction conservative and require both values from nearby text.
        for match in re.finditer(
            r"(?P<brand>[A-Z][A-Za-z0-9&.+\- ]{1,40}?)\s+(?:Air Filter|Cabin Air Filter|Oil Filter|Spark Plug|Serpentine Belt|Wheel Bearing|Brake Pad)[^\n]{0,180}?\b(?P<part>[A-Z0-9][A-Z0-9\-]{3,20})\b",
            page_text,
            flags=re.I,
        ):
            brand = " ".join(match.group("brand").split()).strip()
            part = re.sub(r"[^A-Za-z0-9]", "", match.group("part")).upper()
            if not brand or len(part) < 4:
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
                    confidence=0.35,
                    metadata={
                        "discovery_only": True,
                        "trusted_evidence": False,
                        "search_url": url,
                        "search_text": search_text,
                    },
                )
            )

        return candidates
