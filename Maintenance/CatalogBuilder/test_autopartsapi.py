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
        print("Ping:")
        print(json.dumps(source.ping(), indent=2))
    except Exception as exc:
        print(f"Authentication/connectivity failed: {exc}")
        return 1

    query = CatalogVehicleQuery(make=args.make, model=args.model, year_min=args.year, year_max=args.year, engine=args.engine)
    try:
        resolved = source.resolve_vehicle(query)
    except Exception as exc:
        print(f"Vehicle resolution failed: {exc}")
        return 1

    print("Vehicle resolution:")
    print(json.dumps(resolved, indent=2))
    if resolved.get("reason") != "matched":
        return 3

    print("Model variant probes:")
    for model in resolved.get("model_matches", []):
        if not isinstance(model, dict):
            continue
        name = str(model.get("modelName") or "")
        y0 = str(model.get("modelYearFrom") or "")
        y1 = str(model.get("modelYearTo") or "")
        if args.year and y0[:4].isdigit() and args.year < int(y0[:4]):
            continue
        if args.year and y1[:4].isdigit() and args.year > int(y1[:4]):
            continue
        model_id = model.get("modelId")
        if model_id is None:
            continue
        try:
            probe = source.probe_model_variants(int(model_id))
        except Exception as exc:
            probe = {"model_id": model_id, "error": str(exc)}
        print(name)
        print(json.dumps(probe, indent=2))

    try:
        candidates = source.vehicle_candidates(query)
    except Exception as exc:
        print(f"Vehicle variant lookup failed: {exc}")
        return 1
    print("Vehicle candidates:")
    print(json.dumps(candidates[: max(0, args.limit)], indent=2))
    print(f"Vehicle candidate count: {len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
