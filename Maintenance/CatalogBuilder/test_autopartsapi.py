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
    parser.add_argument("--category", default="engine_air_filter")
    args = parser.parse_args()

    source = AutoPartsApiCandidateSource()
    if not source.configured:
        print("AutoPartsAPI is not configured. Set AUTOSPEC_AUTOPARTS_API_KEY.")
        return 2

    query = CatalogVehicleQuery(
        make=args.make,
        model=args.model,
        year_min=args.year,
        year_max=args.year,
        engine=args.engine,
    )

    print("Ping:")
    print(json.dumps(source.ping(), indent=2))

    resolved = source.resolve_vehicle(query)
    print("Vehicle resolution:")
    print(json.dumps(resolved, indent=2))

    if resolved.get("reason") != "matched":
        return 3

    print("Discovery:")
    candidates = source.discover(query, args.category)
    print(json.dumps([candidate.__dict__ for candidate in candidates], indent=2))
    print(f"Candidate count: {len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
