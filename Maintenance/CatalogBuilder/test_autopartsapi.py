from __future__ import annotations

import argparse
import json

from Maintenance.CatalogBuilder.sources.autopartsapi import AutoPartsApiCandidateSource
from Maintenance.Verify.providers.base import CatalogVehicleQuery


SMOKE_TESTS = {
    "ram": CatalogVehicleQuery(make="Ram", model="1500", year_min=2020, year_max=2020, engine="3.0L Turbo Diesel V6"),
    "honda": CatalogVehicleQuery(make="Honda", model="Accord", year_min=2020, year_max=2020, engine="1.5L Turbo I4"),
    "toyota": CatalogVehicleQuery(make="Toyota", model="Camry", year_min=2020, year_max=2020, engine="2.5L I4"),
    "ford": CatalogVehicleQuery(make="Ford", model="F-150", year_min=2020, year_max=2020, engine="3.5L V6"),
}


def summarize(source: AutoPartsApiCandidateSource, query: CatalogVehicleQuery) -> dict[str, object]:
    resolved = source.resolve_vehicle(query)
    candidates = source.vehicle_candidates(query) if resolved.get("reason") == "matched" else []
    return {
        "query": {
            "make": query.make,
            "model": query.model,
            "year": query.year_min,
            "engine": query.engine,
        },
        "resolution": resolved.get("reason"),
        "model_match_count": len(resolved.get("model_matches", [])),
        "vehicle_candidate_count": len(candidates),
        "top_vehicle_candidates": candidates[:3],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test AutoPartsAPI US-market vehicle coverage.")
    parser.add_argument("--single", choices=tuple(SMOKE_TESTS), help="Run one built-in smoke test only.")
    parser.add_argument("--make")
    parser.add_argument("--model")
    parser.add_argument("--year", type=int)
    parser.add_argument("--engine", default="")
    args = parser.parse_args()

    source = AutoPartsApiCandidateSource()
    if not source.configured:
        print("AutoPartsAPI is not configured. Set AUTOSPEC_AUTOPARTS_API_KEY.")
        return 2

    try:
        print("Ping:")
        print(json.dumps(source.ping(), indent=2))
    except Exception as exc:
        print(f"Authentication/connectivity failed: {exc}")
        return 1

    if args.single:
        tests = (SMOKE_TESTS[args.single],)
    elif args.make and args.model and args.year:
        tests = (
            CatalogVehicleQuery(
                make=args.make,
                model=args.model,
                year_min=args.year,
                year_max=args.year,
                engine=args.engine,
            ),
        )
    else:
        tests = tuple(SMOKE_TESTS.values())

    print("US coverage smoke test:")
    results = []
    for query in tests:
        try:
            results.append(summarize(source, query))
        except Exception as exc:
            results.append({
                "query": {
                    "make": query.make,
                    "model": query.model,
                    "year": query.year_min,
                    "engine": query.engine,
                },
                "error": str(exc),
            })

    print(json.dumps(results, indent=2))
    covered = sum(1 for item in results if int(item.get("vehicle_candidate_count") or 0) > 0)
    print(f"Coverage: {covered}/{len(results)} vehicles returned vehicle candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
