from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from ..models import PartRef, SourceHit
from .base import CatalogProvider, CatalogVehicleQuery

FRAM_BASE_URL = "https://www.fram.com"
FRAM_PART_URL = FRAM_BASE_URL + "/engine-air-filter-{part}"
FRAM_VEHICLE_URL = FRAM_BASE_URL + "/engine-air-filters/{make}/{model}"


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return value.strip("-")


def _text(fragment: str) -> str:
    value = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(value).split())


def _years(value: str) -> tuple[int | None, int | None]:
    years = [int(x) for x in re.findall(r"\b(?:19|20)\d{2}\b", value)]
    if not years:
        return None, None
    return min(years), max(years)


class FramProvider(CatalogProvider):
    name = "FRAM"

    @staticmethod
    def _fetch(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AutoSpecVerification/1.0"})
        with urllib.request.urlopen(req, timeout=20.0) as response:
            return response.read().decode("utf-8", errors="replace")

    def lookup_part(self, part_number: str) -> list[SourceHit]:
        part = re.sub(r"[^A-Za-z0-9]", "", str(part_number or "")).upper()
        query = PartRef(brand=self.name, part_number=part)
        if not part:
            return []
        url = FRAM_PART_URL.format(part=urllib.parse.quote(part.lower()))
        try:
            page = self._fetch(url)
        except Exception:
            return []

        if part not in _text(page).upper():
            return []

        applications: list[dict[str, object]] = []
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, flags=re.I | re.S):
            cells = [_text(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.I | re.S)]
            if len(cells) < 4:
                continue
            year_text, make, model, engine = cells[-4:]
            y0, y1 = _years(year_text)
            if not make or not model or make.lower() == "make":
                continue
            applications.append({"make": make, "model": model, "year_min": y0, "year_max": y1, "engine": engine})

        return [SourceHit(
            source=self.name,
            query=query,
            matched_part=query,
            url=url,
            confidence=1.0 if applications else 0.6,
            notes=f"FRAM catalog returned {len(applications)} applications.",
            metadata={"applications": applications},
        )]

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        make_slug = _slug(query.make)
        model_slug = _slug(query.model)
        if not make_slug or not model_slug:
            return []
        url = FRAM_VEHICLE_URL.format(make=make_slug, model=model_slug)
        try:
            page = self._fetch(url)
        except Exception:
            return []

        text = _text(page)
        candidates = sorted(set(re.findall(r"\bCA\d{4,6}[A-Z]?\b", text, flags=re.I)))
        hits: list[SourceHit] = []
        for candidate in candidates:
            part = candidate.upper()
            verified = self.lookup_part(part)
            if not verified:
                continue
            hits.append(SourceHit(
                source=self.name,
                query=PartRef(brand=f"{query.make} {query.model}".strip(), part_number=str(query.year_min or "")),
                matched_part=PartRef(brand=self.name, part_number=part),
                url=url,
                confidence=0.7,
                notes="Candidate discovered from FRAM vehicle catalog; verify against FRAM applications before approval.",
                metadata={"vehicle_query": {
                    "make": query.make,
                    "model": query.model,
                    "year_min": query.year_min,
                    "year_max": query.year_max,
                    "engine": query.engine,
                }},
            ))
        return hits
