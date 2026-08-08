from __future__ import annotations

from dataclasses import asdict

from Maintenance.Verify.providers.base import CatalogVehicleQuery
from Maintenance.Verify.providers.nhtsa import NhtsaVehicleBackend

from .free_sources import FreeSourceRegistry
from .sources.advance import AdvanceAutoCandidateSource


def default_public_sources() -> FreeSourceRegistry:
    """Return the public discovery sources available in the current environment.

    Sources may be present but unconfigured. That is intentional: discovery remains
    deterministic and safe, while deployments can enable endpoints through environment
    variables without changing verifier code.
    """
    return FreeSourceRegistry(
        sources=(
            AdvanceAutoCandidateSource(),
        )
    )


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

    active_registry = registry or default_public_sources()
    source_results = active_registry.discover(normalized, category)

    total_candidates = sum(len(result.candidates) for result in source_results)
    return {
        "contract": "public_candidate_discovery_v1",
        "category": str(category or "").strip().lower(),
        "query": asdict(query),
        "resolved_vehicle": resolved,
        "candidate_count": total_candidates,
        "sources": [
            {
                "source": result.source,
                "notes": result.notes,
                "candidate_count": len(result.candidates),
                "candidates": [asdict(candidate) for candidate in result.candidates],
            }
            for result in source_results
        ],
    }
