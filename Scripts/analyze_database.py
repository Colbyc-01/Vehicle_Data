import json

# ========= paths =========
ENGINES_PATH = "data/canonical/engines.json"
VEHICLES_PATH = "data/canonical/vehicles.json"

# ========= helpers =========
def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def as_code_list(engine_code):
    """
    engine_code can be:
      - "K20C2"
      - ["K20C2","K24A"]
      - {"code":"K20C2"} or {"engine_code":"K20C2"}
      - [{"code":"K20C2"}, {"engine_code":"K24A"}]
    Returns list[str]
    """
    if engine_code is None:
        return []
    if isinstance(engine_code, str):
        c = engine_code.strip()
        return [c] if c else []
    if isinstance(engine_code, dict):
        c = engine_code.get("code") or engine_code.get("engine_code")
        c = str(c).strip() if c is not None else ""
        return [c] if c else []
    if isinstance(engine_code, list):
        out = []
        for item in engine_code:
            out.extend(as_code_list(item))
        return [c for c in out if c]
    # fallback
    c = str(engine_code).strip()
    return [c] if c else []

def normalize_displacement(x):
    # keep exactly what's stored, but normalize trivial whitespace
    if x is None:
        return ""
    return str(x).strip()

def parse_engine_db(engines_json):
    """
    Supports engine DB shapes:
      - {"engines":[{...},{...}]}
      - [{...},{...}]
      - {"K20C2": {...}, "K24A": {...}}
      - {"some_id": {"code":"K20C2", ...}, ...}
    Returns dict code -> displacement_str
    """
    # figure out where the engine records are
    if isinstance(engines_json, dict) and isinstance(engines_json.get("engines"), list):
        records = engines_json["engines"]
    elif isinstance(engines_json, list):
        records = engines_json
    elif isinstance(engines_json, dict):
        records = list(engines_json.values())
    else:
        records = []

    valid = {}
    for e in records:
        if not isinstance(e, dict):
            continue
        code = e.get("code") or e.get("engine_code")
        if not code:
            continue
        code = str(code).strip()
        if not code:
            continue
        disp = normalize_displacement(e.get("displacement", "Unknown"))
        valid[code] = disp if disp else "Unknown"
    return valid

def extract_engine_displacement_from_vehicle_engine_string(engine_str: str):
    """
    Very simple: for "3.5L V6" returns "3.5L"
    If missing or weird, returns "".
    """
    if not engine_str or not isinstance(engine_str, str):
        return ""
    parts = engine_str.strip().split()
    if not parts:
        return ""
    first = parts[0].strip()
    return first

# ========= main =========
def main():
    engines_json = load_json(ENGINES_PATH)
    vehicles_json = load_json(VEHICLES_PATH)

    valid_codes = parse_engine_db(engines_json)

    print("=" * 80)
    print("ENGINE DATABASE ANALYSIS")
    print("=" * 80)
    print(f"\nTotal engines in engines.json: {len(valid_codes)}")

    if len(valid_codes) <= 200:
        print("\nAll available engine codes and displacements:")
        for code in sorted(valid_codes.keys()):
            print(f"  {code}: {valid_codes[code]}")
    else:
        print("\n(Engine list is large; showing first 50 codes)")
        for code in sorted(valid_codes.keys())[:50]:
            print(f"  {code}: {valid_codes[code]}")

    print("\n" + "=" * 80)
    print("VEHICLES DATABASE ANALYSIS")
    print("=" * 80)

    vehicles_list = []
    if isinstance(vehicles_json, dict) and isinstance(vehicles_json.get("vehicles"), list):
        vehicles_list = vehicles_json["vehicles"]
    elif isinstance(vehicles_json, list):
        vehicles_list = vehicles_json
    else:
        vehicles_list = []

    invalid_codes = {}  # code -> count
    displacement_mismatches = []
    vehicles_without_codes = {}  # engine_str -> list[vehicle_id]

    total_with_code = 0
    total_without_code = 0

    for vehicle in vehicles_list:
        if not isinstance(vehicle, dict):
            continue

        vehicle_id = f"{vehicle.get('year','UNKNOWN')} {vehicle.get('make','UNKNOWN')} {vehicle.get('model','UNKNOWN')}"
        engine_str = vehicle.get("engine", "") or ""
        codes = as_code_list(vehicle.get("engine_code"))

        if codes:
            total_with_code += 1
            for code in codes:
                if code not in valid_codes:
                    invalid_codes[code] = invalid_codes.get(code, 0) + 1
                else:
                    expected = valid_codes[code]
                    actual = extract_engine_displacement_from_vehicle_engine_string(engine_str)

                    # only compare if BOTH look like they have something
                    if expected and expected != "Unknown" and actual and expected != actual:
                        displacement_mismatches.append({
                            "vehicle": vehicle_id,
                            "code": code,
                            "engine_field": engine_str,
                            "expected": expected,
                            "actual": actual
                        })
        else:
            total_without_code += 1
            key = engine_str if isinstance(engine_str, str) else str(engine_str)
            vehicles_without_codes.setdefault(key, []).append(vehicle_id)

    print(f"\nTotal vehicles: {len(vehicles_list)}")
    print(f"Vehicles with engine codes: {total_with_code}")
    print(f"Vehicles without engine codes: {total_without_code}")

    if invalid_codes:
        print(f"\n⚠️ INVALID ENGINE CODES ({len(invalid_codes)} unique):")
        for code, count in sorted(invalid_codes.items(), key=lambda x: (-x[1], x[0]))[:50]:
            print(f"  {code} (used {count} times)")
        if len(invalid_codes) > 50:
            print("  ... (showing top 50)")

    if displacement_mismatches:
        print(f"\n⚠️ DISPLACEMENT MISMATCHES ({len(displacement_mismatches)}):")
        for m in displacement_mismatches[:20]:
            print(f"  {m['vehicle']}")
            print(f"    Code: {m['code']}")
            print(f"    Engine field: {m['engine_field']}")
            print(f"    Expected: {m['expected']}  Got: {m['actual']}")
        if len(displacement_mismatches) > 20:
            print("  ... (showing first 20)")

    print(f"\n⚠️ VEHICLES WITHOUT ENGINE CODES ({len(vehicles_without_codes)} unique engine strings):")
    for eng, vlist in sorted(vehicles_without_codes.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
        print(f"  '{eng}' ({len(vlist)} vehicles)")

if __name__ == "__main__":
    main()
