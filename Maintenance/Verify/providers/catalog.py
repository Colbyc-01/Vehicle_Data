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

    @staticmethod
    def _query_from_resolved(query: CatalogVehicleQuery, resolved: list[dict[str, object]]) -> CatalogVehicleQuery:
        if not resolved:
            return query
        item = resolved[0]
        year = item.get("year")
        return CatalogVehicleQuery(
            make=str(item.get("make") or query.make),
            model=str(item.get("model") or query.model),
            year_min=year if isinstance(year, int) else query.year_min,
            year_max=year if isinstance(year, int) else query.year_max,
            engine=str(item.get("engine") or query.engine),
        )

    def discover(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[CatalogPartCandidate]:
        category_key = str(category or "").strip().lower()
        if not category_key:
            return []

        resolved = self.resolve_vehicle(query)
        normalized_query = self._query_from_resolved(query, resolved)
        candidates: list[CatalogPartCandidate] = []
        seen: set[tuple[str, str, str]] = set()

        for backend in self.backends:
            for candidate in backend.lookup_vehicle_parts(normalized_query, category_key):
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
                metadata = dict(candidate.metadata or {})
                if resolved:
                    metadata.setdefault("resolved_vehicle", resolved[0])
                candidates.append(
                    CatalogPartCandidate(
                        category=candidate.category,
                        brand=candidate.brand,
                        part_number=candidate.part_number,
                        source=candidate.source,
                        confidence=candidate.confidence,
                        metadata=metadata,
                    )
                )
        return candidates

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        return []
