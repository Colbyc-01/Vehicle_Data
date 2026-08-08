from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

from ..models import PartRef, SourceHit
from .base import CatalogProvider, CatalogVehicleQuery

FRAM_BASE_URL = "https://www.fram.com"
FRAM_PART_URL = FRAM_BASE_URL + "/engine-air-filter-{part}"
FRAM_MODEL_URL = FRAM_BASE_URL + "/engine-air-filters/{make}/{model}"
FRAM_YEAR_URL = FRAM_MODEL_URL + "/{year}"


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


def _engine_displacement(value: str) -> str:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*[lL]\b", str(value or ""))
    return match.group(1) if match else ""


def _engine_matches(query_engine: str, catalog_engine: str) -> bool:
    q = _engine_displacement(query_engine)
    c = _engine_displacement(catalog_engine)
    if q and c and q != c:
        return False
    q_text = str(query_engine or "").lower()
    c_text = str(catalog_engine or "").lower()
    if "diesel" in q_text and "diesel" not in c_text:
        return False
    if "turbo" in q_text and c_text and "turbo" not in c_text:
        # FRAM pages do not always spell turbo out, so displacement is still the
        # primary discriminator. Do not reject a matching diesel engine solely here.
        if "diesel" not in q_text:
            return False
    return True


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

    @staticmethod
    def _links(page: str) -> list[tuple[str, str]]:
        links: list[tuple[str, str]] = []
        for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page, flags=re.I | re.S):
            links.append((html.unescape(href), _text(label)))
        return links

    def _candidate_parts_from_page(self, page: str) -> list[str]:
        candidates = {value.upper() for value in re.findall(r"\bCA\d{3,6}[A-Z]?\b", _text(page), flags=re.I)}
        for href, label in self._links(page):
            for value in re.findall(r"\bCA\d{3,6}[A-Z]?\b", f"{href} {label}", flags=re.I):
                candidates.add(value.upper())
        return sorted(candidates)

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        make_slug = _slug(query.make)
        model_slug = _slug(query.model)
        if not make_slug or not model_slug:
            return []

        years: list[int] = []
        if query.year_min is not None and query.year_max is not None:
            lo, hi = sorted((query.year_min, query.year_max))
            years = list(range(lo, hi + 1))
        elif query.year_min is not None:
            years = [query.year_min]
        elif query.year_max is not None:
            years = [query.year_max]

        pages: list[tuple[str, str]] = []
        if years:
            for year in years:
                url = FRAM_YEAR_URL.format(make=make_slug, model=model_slug, year=year)
                try:
                    pages.append((url, self._fetch(url)))
                except Exception:
                    continue
        else:
            url = FRAM_MODEL_URL.format(make=make_slug, model=model_slug)
            try:
                pages.append((url, self._fetch(url)))
            except Exception:
                return []

        discovered: dict[str, str] = {}
        for page_url, page in pages:
            for part in self._candidate_parts_from_page(page):
                discovered.setdefault(part, page_url)

            # FRAM year pages can be an engine-selection page. Follow links whose
            # visible engine text matches the requested displacement/fuel type.
            for href, label in self._links(page):
                if not _engine_matches(query.engine, label):
                    continue
                if "engine-air-filter" not in href.lower() and "engine-air-filters" not in href.lower():
                    continue
                engine_url = urllib.parse.urljoin(FRAM_BASE_URL, href)
                try:
                    engine_page = self._fetch(engine_url)
                except Exception:
                    continue
                for part in self._candidate_parts_from_page(engine_page):
                    discovered.setdefault(part, engine_url)

        hits: list[SourceHit] = []
        for part, source_url in sorted(discovered.items()):
            verified = self.lookup_part(part)
            if not verified:
                continue
            hits.append(SourceHit(
                source=self.name,
                query=PartRef(brand=f"{query.make} {query.model}".strip(), part_number=str(query.year_min or "")),
                matched_part=PartRef(brand=self.name, part_number=part),
                url=source_url,
                confidence=0.7,
                notes="Candidate discovered from FRAM year/engine catalog; verify against FRAM applications before approval.",
                metadata={"vehicle_query": {
                    "make": query.make,
                    "model": query.model,
                    "year_min": query.year_min,
                    "year_max": query.year_max,
                    "engine": query.engine,
                }},
            ))
        return hits
