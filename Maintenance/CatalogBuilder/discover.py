from __future__ import annotations

from dataclasses import asdict

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.nhtsa import NhtsaVehicleBackend

from .free_sources import FreeSourceRegistry


def discover_public_candidates(
    query: CatalogVehicleQuery,
    category: str,
    registry: FreeSourceRegistry | None = None,
) -> dict[str, object]:
    """Resolve a canonical vehicle and run configured free/public discovery sources.

    This does not mark any part verified. It only produces candidate evidence for the
    downstream verification pipeline.
    """
    resolver = NhtsaVehicleBackend()
    resolved = resolver.resolve_vehicle(query)
    normalized = CatalogVehicleQuery(
        make=str(resolved.get("make") or query.make),
        model=str(resolved.get("model") or query.model),
        year_min=resolved.get("year") if isinstance(resolved.get("year"), int) else query.year_min,
        year_max=resolved.get("year") if isinstance(resolved.get("year"), int) else query.year_max,
        engine=str(resolved.get("engine") or query.engine),
    )

    active_registry = registry or FreeSourceRegistry()
    source_results = active_registry.discover(normalized, category)

    return {
        "contract": "public_candidate_discovery_v1",
        "category": str(category or "").strip().lower(),
        "query": asdict(query),
        "resolved_vehicle": resolved,
        "sources": [
            {
                "source": result.source,
                "notes": result.notes,
                "candidates": [asdict(candidate) for candidate in result.candidates],
            }
            for result in source_results
        ],
    }
