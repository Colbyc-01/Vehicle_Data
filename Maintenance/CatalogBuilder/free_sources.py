from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.catalog import CatalogPartCandidate


class FreeCandidateSource(Protocol):
    name: str

    def discover(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[CatalogPartCandidate]: ...


@dataclass(frozen=True)
class SourceResult:
    source: str
    candidates: tuple[CatalogPartCandidate, ...]
    notes: str = ""


class FreeSourceRegistry:
    """Registry for free/public candidate discovery sources.

    Sources are discovery-only. Returned parts are never treated as verified fitment
    until downstream manufacturer/application checks succeed.
    """

    def __init__(self, sources: tuple[FreeCandidateSource, ...] = ()):
        self.sources = sources

    def discover(
        self,
        query: CatalogVehicleQuery,
        category: str,
    ) -> list[SourceResult]:
        results: list[SourceResult] = []
        for source in self.sources:
            try:
                candidates = tuple(source.discover(query, category))
                results.append(SourceResult(source=source.name, candidates=candidates))
            except Exception as exc:
                results.append(SourceResult(source=source.name, candidates=(), notes=str(exc)))
        return results
