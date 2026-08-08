from __future__ import annotations

import argparse
import json

from Maintenance.CatalogBuilder.sources.autopartsapi import AutoPartsApiCandidateSource
from Maintenance.Verify.providers.base import CatalogVehicleQuery


def main() -> int:
    parser = argparse.ArgumentParser(description="Test AutoPartsAPI connectivity and staged vehicle resolution.")
    parser.add_argument("--make", default="Ram")
    parser.add_argument("--model", default="1500")
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--engine", default="3.0L Turbo Diesel V6")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    source = AutoPartsApiCandidateSource()
    if not source.configured:
        print("AutoPartsAPI is not configured. Set AUTOSPEC_AUTOPARTS_API_KEY.")
        return 2

    try:
        ping = source.ping()
    except Exception as exc:
        print(f"Authentication/connectivity failed: {exc}")
        return 1

    print("Ping:")
    print(json.dumps(ping, indent=2))

    query = CatalogVehicleQuery(
        make=args.make,
        model=args.model,
        year_min=args.year,
        year_max=args.year,
        engine=args.engine,
    )

    try:
        resolved = source.resolve_vehicle(query)
    except Exception as exc:
        print(f"Vehicle resolution failed: {exc}")
        return 1

    print("Vehicle resolution:")
    print(json.dumps(resolved, indent=2))
    if resolved.get("reason") != "matched":
        return 3

    try:
        vehicle_candidates = source.vehicle_candidates(query)
    except Exception as exc:
        print(f"Vehicle variant lookup failed: {exc}")
        return 1

    print("Vehicle candidates:")
    print(json.dumps(vehicle_candidates[: max(0, args.limit)], indent=2))
    print(f"Vehicle candidate count: {len(vehicle_candidates)}")

    try:
        discovered = source.discover(query, "engine_air_filter")
    except Exception as exc:
        print(f"Discovery failed: {exc}")
        return 1

    print("Discovery:")
    print(json.dumps([candidate.__dict__ for candidate in discovered], indent=2))
    print(f"Candidate count: {len(discovered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
