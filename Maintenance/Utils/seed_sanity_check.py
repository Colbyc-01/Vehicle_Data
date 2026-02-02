#!/usr/bin/env python3
"""Seed sanity check v3 (read-only).

Run from repo root:
  python Maintenance/Contracts/utils/seed_sanity_check.py

Optional env overrides:
  VEHICLES_JSON, ENGINES_JSON,
  OIL_CAPACITY_SEED, OIL_SPECS_SEED, OIL_CHANGE_PARTS_SEED,
  ENGINE_AIR_FILTER_SEED, CABIN_AIR_FILTER_SEED, WIPER_BLADES_SEED, BATTERY_SEED, HEADLIGHT_BULBS_SEED
"""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _first_existing(candidates: List[Optional[str]]) -> Optional[str]:
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def _resolve_paths(repo_root: str) -> Dict[str, str]:
    env = os.environ

    vehicles_candidates = [
        env.get("VEHICLES_JSON"),
        os.path.join(repo_root, "data", "canonical", "vehicles.json"),
        os.path.join(repo_root, "vehicles.json"),
    ]
    engines_candidates = [
        env.get("ENGINES_JSON"),
        os.path.join(repo_root, "data", "canonical", "engines.json"),
        os.path.join(repo_root, "engines.json"),
    ]

    seed_dirs = [
        os.path.join(repo_root, "Maintenance", "Seeds"),
        os.path.join(repo_root, "Maintenance", "Contracts", "Seeds"),
    ]

    def seed_path(env_key: str, filename: str) -> Optional[str]:
        override = env.get(env_key)
        if override and os.path.exists(override):
            return override
        for d in seed_dirs:
            p = os.path.join(d, filename)
            if os.path.exists(p):
                return p
        return None

    resolved = {
        "vehicles": _first_existing(vehicles_candidates),
        "engines": _first_existing(engines_candidates),

        # oil (engine-based)
        "oil_capacity": seed_path("OIL_CAPACITY_SEED", "oil_capacity_seed.json"),
        "oil_specs": seed_path("OIL_SPECS_SEED", "oil_specs_seed.json"),
        "oil_change_parts": seed_path("OIL_CHANGE_PARTS_SEED", "oil_change_parts_seed.json"),

        # new seeds
        "engine_air_filter": seed_path("ENGINE_AIR_FILTER_SEED", "engine_air_filter_seed.json"),
        "cabin_air_filter": seed_path("CABIN_AIR_FILTER_SEED", "cabin_air_filter_seed.json"),
        "wiper_blades": seed_path("WIPER_BLADES_SEED", "wiper_blades_seed.json"),
        "battery": seed_path("BATTERY_SEED", "battery_seed.json"),
        "headlight_bulbs": seed_path("HEADLIGHT_BULBS_SEED", "headlight_bulbs_seed.json"),
    }

    # Required only: vehicles + engines + oil seeds
    required = ["vehicles", "engines", "oil_capacity", "oil_specs", "oil_change_parts"]
    missing_required = [k for k in required if not resolved.get(k)]
    if missing_required:
        raise FileNotFoundError(
            "Missing required files: "
            + ", ".join(missing_required)
            + "\nSet env vars or place files in expected repo locations.\n"
            + "\n".join([f"  {k}: {resolved.get(k)}" for k in resolved.keys()])
        )

    # Optional seeds may be absent; we still report if missing.
    return resolved  # type: ignore


def _vehicle_engine_codes(vehicles_obj: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for v in vehicles_obj.get("vehicles", []):
        for ec in (v.get("engine_codes") or []):
            if isinstance(ec, str) and ec.strip():
                out.append(ec.strip())
    return out


def _vehicle_keys(vehicles_obj: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for v in vehicles_obj.get("vehicles", []):
        make = v.get("make")
        model = v.get("model")
        yrs = v.get("years") or {}
        y0 = yrs.get("min")
        y1 = yrs.get("max")
        if make and model and isinstance(y0, int) and isinstance(y1, int):
            out.append(f"{make}_{model}_{y0}_{y1}")
    return out


def _seed_engine_codes(seed_obj: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for it in seed_obj.get("items", []):
        if not isinstance(it, dict):
            continue
        ec = it.get("engine_code")
        if isinstance(ec, str) and ec.strip():
            out.append(ec.strip())
    return out


def _seed_vehicle_keys(seed_obj: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for it in seed_obj.get("items", []):
        if not isinstance(it, dict):
            continue
        vk = it.get("vehicle_key")
        if isinstance(vk, str) and vk.strip():
            out.append(vk.strip())
    return out


def _dupes(values: List[str]) -> Dict[str, int]:
    c = Counter(values)
    return {k: v for k, v in c.items() if v > 1}


def _print_top_missing(missing: List[str], counts: Counter, n: int = 20) -> None:
    ranked = sorted(set(missing), key=lambda x: (-counts.get(x, 0), x))
    for x in ranked[:n]:
        print(f"    - {x} (refs={counts.get(x, 0)})")


def _report_engine_seed(name: str, seed_obj: Dict[str, Any], vehicle_set: Set[str], vehicle_counts: Counter, engines_set: Set[str]) -> Tuple[Set[str], Dict[str, int], List[str]]:
    codes = _seed_engine_codes(seed_obj)
    dupes = _dupes(codes)
    seed_set = set(codes)

    covered = len(vehicle_set & seed_set)
    missing = list(vehicle_set - seed_set)

    unk = sorted([ec for ec in seed_set if ec not in engines_set])

    print(f"{name}:")
    print(f"  seed entries (unique): {len(seed_set)}")
    print(f"  covered:              {covered}")
    print(f"  missing:              {len(missing)}")
    if dupes:
        print(f"  DUPLICATES:           {len(dupes)} (should be 0)")
    print("  Top missing:")
    _print_top_missing(missing, vehicle_counts, n=20)
    print(f"  engine_codes missing from engines.json: {len(unk)}")
    print("")
    return seed_set, dupes, unk


def _report_vehicle_seed(name: str, seed_obj: Dict[str, Any], vehicle_key_set: Set[str], vehicle_key_counts: Counter) -> Tuple[Set[str], Dict[str, int]]:
    keys = _seed_vehicle_keys(seed_obj)
    dupes = _dupes(keys)
    seed_set = set(keys)

    covered = len(vehicle_key_set & seed_set)
    missing = list(vehicle_key_set - seed_set)

    print(f"{name}:")
    print(f"  seed entries (unique): {len(seed_set)}")
    print(f"  covered:              {covered}")
    print(f"  missing:              {len(missing)}")
    if dupes:
        print(f"  DUPLICATES:           {len(dupes)} (should be 0)")
    print("  Top missing vehicle_keys:")
    _print_top_missing(missing, vehicle_key_counts, n=20)
    print("")
    return seed_set, dupes


def main() -> int:
    repo_root = os.getcwd()
    try:
        paths = _resolve_paths(repo_root)
    except FileNotFoundError as e:
        print(str(e))
        return 2

    vehicles = _load_json(paths["vehicles"])
    engines = _load_json(paths["engines"])

    if not isinstance(vehicles, dict) or "vehicles" not in vehicles:
        print("ERROR: vehicles.json must be an object with a 'vehicles' array.")
        return 2
    if not isinstance(engines, dict):
        print("ERROR: engines.json must be an object keyed by engine_code.")
        return 2

    # vehicle sets + counts
    vehicle_codes = _vehicle_engine_codes(vehicles)
    vehicle_set = set(vehicle_codes)
    vehicle_counts = Counter(vehicle_codes)

    vehicle_keys = _vehicle_keys(vehicles)
    vehicle_key_set = set(vehicle_keys)
    vehicle_key_counts = Counter(vehicle_keys)

    engines_set = set(engines.keys())

    print("Resolved paths:")
    for k, v in paths.items():
        if v:
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: (missing/optional)")
    print("")

    print(f"Vehicle engine codes (unique): {len(vehicle_set)}")
    print(f"Vehicle keys (unique):        {len(vehicle_key_set)}")
    print("")

    # Required oil seeds
    oil_cap = _load_json(paths["oil_capacity"])
    oil_specs = _load_json(paths["oil_specs"])
    oil_parts = _load_json(paths["oil_change_parts"])

    cap_set, cap_dupes, cap_unk = _report_engine_seed("Oil capacity", oil_cap, vehicle_set, vehicle_counts, engines_set)
    specs_set, specs_dupes, specs_unk = _report_engine_seed("Oil specs", oil_specs, vehicle_set, vehicle_counts, engines_set)
    parts_set, parts_dupes, parts_unk = _report_engine_seed("Oil change parts (filters)", oil_parts, vehicle_set, vehicle_counts, engines_set)

    # Optional seeds
    exit_code = 0
    if paths.get("engine_air_filter"):
        eng_air = _load_json(paths["engine_air_filter"])
        _report_engine_seed("Engine air filters", eng_air, vehicle_set, vehicle_counts, engines_set)
    else:
        print("Engine air filters: (seed missing/optional)\n")

    if paths.get("cabin_air_filter"):
        cabin = _load_json(paths["cabin_air_filter"])
        _report_vehicle_seed("Cabin air filters", cabin, vehicle_key_set, vehicle_key_counts)
    else:
        print("Cabin air filters: (seed missing/optional)\n")

    if paths.get("wiper_blades"):
        wipers = _load_json(paths["wiper_blades"])
        _report_vehicle_seed("Wiper blades", wipers, vehicle_key_set, vehicle_key_counts)
    else:
        print("Wiper blades: (seed missing/optional)\n")

    if paths.get("battery"):
        batt = _load_json(paths["battery"])
        _report_vehicle_seed("Battery", batt, vehicle_key_set, vehicle_key_counts)
    else:
        print("Battery: (seed missing/optional)\n")

    if paths.get("headlight_bulbs"):
        bulbs = _load_json(paths["headlight_bulbs"])
        _report_vehicle_seed("Headlight bulbs", bulbs, vehicle_key_set, vehicle_key_counts)
    else:
        print("Headlight bulbs: (seed missing/optional)\n")

    # Hard fail only on duplicates in required seeds
    if cap_dupes or specs_dupes or parts_dupes:
        print("FAIL: Duplicate keys detected in required oil seeds.")
        exit_code = 1

    if exit_code == 0:
        print("OK")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
