from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


_BRAND_ALIASES = {
    "AC DELCO": "ACDelco",
    "ACDELCO": "ACDelco",
    "K AND N": "K&N",
    "K&N": "K&N",
    "MANN FILTER": "MANN",
    "MANN-FILTER": "MANN",
    "MAHLE ORIGINAL": "Mahle",
    "MOPAR": "Mopar",
    "MOTORCRAFT": "Motorcraft",
    "PUROLATOR": "Purolator",
    "FRAM": "FRAM",
    "WIX": "WIX",
}


def normalize_brand(value: Any) -> str:
    raw = " ".join(str(value or "").strip().split())
    if not raw:
        return ""
    key = re.sub(r"\s+", " ", raw.upper()).strip()
    return _BRAND_ALIASES.get(key, raw)


def normalize_part_number(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class NormalizedCatalogRecord:
    category: str
    brand: str
    part_number: str
    make: str = ""
    model: str = ""
    year_min: int | None = None
    year_max: int | None = None
    engine: str = ""
    source: str = ""
    confidence: float = 0.0
    verified: bool = False
    provenance: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple[object, ...]:
        return (
            self.category.lower(),
            self.brand.upper(),
            self.part_number.upper(),
            self.make.upper(),
            self.model.upper(),
            self.year_min,
            self.year_max,
            self.engine.upper(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "brand": self.brand,
            "part_number": self.part_number,
            "make": self.make,
            "model": self.model,
            "year_min": self.year_min,
            "year_max": self.year_max,
            "engine": self.engine,
            "source": self.source,
            "confidence": self.confidence,
            "verified": self.verified,
            "provenance": list(self.provenance),
            "metadata": self.metadata,
        }


def normalize_record(item: dict[str, Any]) -> NormalizedCatalogRecord | None:
    category = normalize_text(item.get("category")).lower()
    brand = normalize_brand(item.get("brand") or item.get("manufacturer"))
    part_number = normalize_part_number(
        item.get("part_number") or item.get("partNumber") or item.get("part_no") or item.get("partNo") or item.get("sku")
    )
    if not category or not brand or not part_number:
        return None

    def as_year(value: Any) -> int | None:
        try:
            year = int(value)
        except (TypeError, ValueError):
            return None
        return year if 1886 <= year <= 2200 else None

    confidence_raw = item.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence_raw)))
    except (TypeError, ValueError):
        confidence = 0.0

    source = normalize_text(item.get("source") or item.get("dataset") or item.get("origin"))
    provenance_raw = item.get("provenance")
    provenance: list[str] = []
    if isinstance(provenance_raw, list):
        provenance.extend(normalize_text(value) for value in provenance_raw if normalize_text(value))
    elif normalize_text(provenance_raw):
        provenance.append(normalize_text(provenance_raw))
    if source and source not in provenance:
        provenance.append(source)

    known = {
        "category", "brand", "manufacturer", "part_number", "partNumber", "part_no", "partNo", "sku",
        "make", "model", "year", "year_min", "year_max", "engine", "source", "dataset", "origin",
        "confidence", "verified", "provenance", "metadata",
    }
    metadata = dict(item.get("metadata") or {}) if isinstance(item.get("metadata"), dict) else {}
    metadata.update({key: value for key, value in item.items() if key not in known})

    year = as_year(item.get("year"))
    year_min = as_year(item.get("year_min")) or year
    year_max = as_year(item.get("year_max")) or year

    return NormalizedCatalogRecord(
        category=category,
        brand=brand,
        part_number=part_number,
        make=normalize_text(item.get("make")),
        model=normalize_text(item.get("model")),
        year_min=year_min,
        year_max=year_max,
        engine=normalize_text(item.get("engine")),
        source=source,
        confidence=confidence,
        verified=bool(item.get("verified", False)),
        provenance=tuple(dict.fromkeys(provenance)),
        metadata=metadata,
    )
