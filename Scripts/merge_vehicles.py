import json
import hashlib
from pathlib import Path

CANON = Path("data/canonical/vehicles.json")
SRC_DIR = Path("data/sources")

def load_vehicles(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("vehicles"), list):
        return data["vehicles"]
    if isinstance(data, list):
        return data
    return []

def norm_str(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip().lower()
    return str(x).strip().lower()

def norm_engine_code(ec):
    # engine_code can be "K20C2" OR ["K20C2","K24A"] OR [{"code":...}]
    if ec is None:
        return ""
    if isinstance(ec, str):
        return ec.strip().lower()
    if isinstance(ec, list):
        parts = []
        for item in ec:
            if isinstance(item, str):
                parts.append(item.strip().lower())
            elif isinstance(item, dict) and "engine_code" in item:
                parts.append(str(item["engine_code"]).strip().lower())
            elif isinstance(item, dict) and "code" in item:
                parts.append(str(item["code"]).strip().lower())
            else:
                parts.append(str(item).strip().lower())
        parts = sorted([p for p in parts if p])
        return ",".join(parts)
    if isinstance(ec, dict):
        if "engine_code" in ec:
            return str(ec["engine_code"]).strip().lower()
        if "code" in ec:
            return str(ec["code"]).strip().lower()
    return str(ec).strip().lower()

def key(v: dict) -> str:
    year = v.get("year", "")
    make = norm_str(v.get("make"))
    model = norm_str(v.get("model"))
    trim = norm_str(v.get("trim"))
    engine_code = norm_engine_code(v.get("engine_code"))

    raw = f"{year}|{make}|{model}|{trim}|{engine_code}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
def merge(dst: dict, src: dict):
    # Fill missing fields; do not overwrite populated ones
    for k, v in src.items():
        if k not in dst or dst[k] in (None, "", [], {}):
            dst[k] = v

def main():
    if not CANON.exists():
        raise FileNotFoundError(f"Missing {CANON}")
    if not SRC_DIR.exists():
        raise FileNotFoundError(f"Missing {SRC_DIR}")

    merged = {}

    base = load_vehicles(CANON)
    for v in base:
        merged[key(v)] = v

    for p in sorted(SRC_DIR.glob("*.json")):
        for v in load_vehicles(p):
            k = key(v)
            if k not in merged:
                merged[k] = v
            else:
                merge(merged[k], v)

    out = {
        "version": "vehicles.v1",
        "scope": "US-only",
        "vehicles": list(merged.values()),
    }
    CANON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"✅ vehicles.json now has {len(out['vehicles'])} vehicles")

if __name__ == "__main__":
    main()
