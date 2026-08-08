from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import SourceHit
from .base import CatalogVehicleQuery


@dataclass(frozen=True)
class CatalogPartCandidate:
    category: str
    brand: str
    part_number: str
    source: str
    confidence: float = 0.0
    metadata: dict[str, object] | None = None


class StructuredCatalogBackend(Protocol):
    name: str

    def lookup_vehicle_parts(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[CatalogPartCandidate]: ...


class StructuredCatalogProvider:
    """Category-agnostic discovery front-end for structured vehicle/parts catalogs.

    Manufacturer-specific providers remain useful as fitment verifiers. This provider
    is intentionally separate: its job is vehicle -> candidate part discovery across
    maintenance categories, while downstream provider/application checks decide whether
    a candidate can be trusted.
    """

    name = "catalog"

    def __init__(self, backend: StructuredCatalogBackend):
        self.backend = backend

    def discover(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[CatalogPartCandidate]:
        category_key = str(category or "").strip().lower()
        if not category_key:
            return []
        return [
            candidate
            for candidate in self.backend.lookup_vehicle_parts(query, category_key)
            if candidate.part_number and candidate.brand
        ]

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        # The generic provider requires an explicit category. Keeping the base-shaped
        # method prevents accidental category-less discovery.
        return []
