from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from Maintenance.Verify.providers.catalog import CatalogPartCandidate


_FIELD_ALIASES = {
    "category": ("category", "part_category", "maintenance_category"),
    "brand": ("brand", "manufacturer", "mfr"),
    "part_number": ("part_number", "partnumber", "part_no", "partno", "sku", "mpn"),
    "make": ("make", "vehicle_make"),
    "model": ("model", "vehicle_model"),
    "year": ("year", "model_year"),
    "engine": ("engine", "engine_label", "engine_description"),
    "source": ("source", "catalog", "dataset"),
}


def _first(row: dict[str, object], names: Iterable[str]) -> str:
    lower = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lower.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def normalize_row(row: dict[str, object], default_source: str) -> dict[str, object] | None:
    category = _first(row, _FIELD_ALIASES["category"]).lower()
    brand = _first(row, _FIELD_ALIASES["brand"])
    part_number = _first(row, _FIELD_ALIASES["part_number"])
    if not category or not brand or not part_number:
        return None

    year_text = _first(row, _FIELD_ALIASES["year"])
    try:
        year = int(year_text) if year_text else None
    except ValueError:
        year = None

    source = _first(row, _FIELD_ALIASES["source"]) or default_source
    candidate = CatalogPartCandidate(
        category=category,
        brand=brand,
        part_number=part_number,
        source=source,
        confidence=0.3,
        metadata={
            "discovery_only": True,
            "trusted_evidence": False,
            "vehicle": {
                "year": year,
                "make": _first(row, _FIELD_ALIASES["make"]),
                "model": _first(row, _FIELD_ALIASES["model"]),
                "engine": _first(row, _FIELD_ALIASES["engine"]),
            },
            "raw": row,
        },
    )
    return asdict(candidate)


def load_csv(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, object]] = []
        for row in reader:
            normalized = normalize_row(dict(row), path.name)
            if normalized:
                rows.append(normalized)
        return rows


def load_json(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("parts", "records", "items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                payload = value
                break
    if not isinstance(payload, list):
        return []

    rows: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized = normalize_row(item, path.name)
        if normalized:
            rows.append(normalized)
    return rows


def import_dataset(path: str | Path) -> dict[str, object]:
    source_path = Path(path)
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        records = load_csv(source_path)
    elif suffix == ".json":
        records = load_json(source_path)
    else:
        raise ValueError(f"Unsupported dataset format: {source_path.suffix}")

    return {
        "contract": "catalog_import_v1",
        "source_file": str(source_path),
        "record_count": len(records),
        "records": records,
    }
