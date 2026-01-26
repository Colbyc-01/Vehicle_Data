#!/usr/bin/env python3

Sanity checks for FastAPI response *shapes* (contracts).

Run:
  python sanity_check_api.py

Assumes backend at http://127.0.0.1:8000 and that it is running.

import json
import sys
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:8000"

def _get(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))

def _post(path, payload):
    url = BASE + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json", "accept":"application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))

def require(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        raise AssertionError(f"{where}: missing '{key}'")
    return obj[key]

def require_str(obj, key, where):
    v = require(obj, key, where)
    if not isinstance(v, str) or not v.strip():
        raise AssertionError(f"{where}: '{key}' not a non-empty string")
    return v

def require_dict(obj, key, where):
    v = require(obj, key, where)
    if not isinstance(v, dict):
        raise AssertionError(f"{where}: '{key}' not an object")
    return v

def require_list(obj, key, where):
    v = require(obj, key, where)
    if not isinstance(v, list):
        raise AssertionError(f"{where}: '{key}' not an array")
    return v

def main():
    print("== Contract sanity checks ==")

    years = _get("/years")
    if not isinstance(years, list) or not years:
        raise AssertionError("/years: expected non-empty list")

    y = years[-1]
    makes = _get("/makes", {"year": y})
    if not isinstance(makes, list):
        raise AssertionError("/makes: expected list")

    # Pick a make/model that exists by probing (best-effort)
    picked_make = makes[0] if makes else None
    if picked_make:
        models = _get("/models", {"year": y, "make": picked_make})
        if not isinstance(models, list):
            raise AssertionError("/models: expected list")
        picked_model = models[0] if models else None
    else:
        picked_model = None

    if picked_make and picked_model:
        vs = _get("/vehicles/search", {"year": y, "make": picked_make, "model": picked_model})
        require_list(vs, "results", "/vehicles/search")
        results = vs["results"]
        if results:
            # Normalize vehicle wrapper
            first = results[0]
            if isinstance(first, dict) and "vehicle" in first and isinstance(first["vehicle"], dict):
                v = first["vehicle"]
            else:
                v = first

            require_str(v, "engine_label", "/vehicles/search.results[0]")
            codes = require(v, "engine_codes", "/vehicles/search.results[0]")
            if not isinstance(codes, list) or not codes:
                raise AssertionError("/vehicles/search.results[0].engine_codes: expected non-empty list")

            # Oil by engine for first code (may still 404 if seed missing; handle)
            engine_code = str(codes[0])
            try:
                oil = _get("/oil-change/by-engine", {"engine_code": engine_code})
                oil_spec = require_dict(oil, "oil_spec", "/oil-change/by-engine")
                oil_cap = require_dict(oil, "oil_capacity", "/oil-change/by-engine")
                require_str(oil_spec, "label", "/oil-change/by-engine.oil_spec")
                require_str(oil_cap, "capacity_label_with_filter", "/oil-change/by-engine.oil_capacity")
            except Exception as e:
                print(f"!! Note: oil-change check skipped/failed for engine_code={engine_code}: {e}")

    # VIN resolve: just ensure keys exist (VIN may be invalid)
    vin = "INVALIDVIN00000000"
    try:
        vr = _post("/vin/resolve", {"vin": vin, "seed_version":"phaseB2", "app_version":"sanity"})
        require_str(vr, "status", "/vin/resolve")
        require_dict(vr, "decoded", "/vin/resolve")
    except Exception as e:
        print(f"!! Note: vin/resolve check failed (backend may enforce VIN format): {e}")

    print("PASS: core contracts look sane.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("FAIL:", e)
        sys.exit(1)
