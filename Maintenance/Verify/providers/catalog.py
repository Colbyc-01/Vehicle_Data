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
    """Category-agnostic discovery front-end for structured vehicle/parts catalogs."""

    name = "catalog"

    def __init__(self, backends: StructuredCatalogBackend | tuple[StructuredCatalogBackend, ...]):
        if isinstance(backends, tuple):
            self.backends = backends
        else:
            self.backends = (backends,)

    def discover(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[CatalogPartCandidate]:
        category_key = str(category or "").strip().lower()
        if not category_key:
            return []

        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str, str]] = set()
        for backend in self.backends:
            for candidate in backend.lookup_vehicle_parts(query, category_key):
                if not candidate.part_number or not candidate.brand:
                    continue
                key = (
                    candidate.brand.strip().upper(),
                    candidate.part_number.strip().upper(),
                    candidate.category.strip().lower(),
                )
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(candidate)
        return candidates

    def resolve_vehicle(self, query: CatalogVehicleQuery) -> list[dict[str, object]]:
        """Return normalized vehicle identities from backends that support resolution."""
        resolved: list[dict[str, object]] = []
        for backend in self.backends:
            resolver = getattr(backend, "resolve_vehicle", None)
            if resolver is None:
                continue
            result = resolver(query)
            if isinstance(result, dict) and result:
                resolved.append({"backend": backend.name, **result})
        return resolved

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        return []
