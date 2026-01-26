from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sqlite3
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).parent
ROOT = BASE.parent

DATA = ROOT / "data" / "canonical"
SEEDS = ROOT / "Maintenance" / "Seeds"

VEHICLES_PATH = DATA / "vehicles.json"
OIL_SPECS_PATH = SEEDS / "oil_specs_seed.json"
OIL_CAPACITY_PATH = SEEDS / "oil_capacity_seed.json"
OIL_PARTS_PATH = SEEDS / "oil_change_parts_seed.json"

# Absolute, stable DB path (prevents CWD-dependent failures when running uvicorn)
VIN_DB_PATH = ROOT / "Maintenance" / "Data" / "vin_events.db"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_to_raw(code: str) -> Optional[str]:
    if not code:
        return None
    if "_" in code:
        return code.split("_", 1)[1]
    return code


def as_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


def norm(s: Any) -> str:
    if s is None:
        return ""
    return " ".join(str(s).strip().split()).casefold()


# ---------------- Oil spec labeling / verification ----------------

_BRAND_LABELS = {
    "gm": "GM",
    "dexos1": "dexos1",
    "dexos": "dexos",
    "ford": "Ford",
    "toyota": "Toyota",
    "honda": "Honda",
    "nissan": "Nissan",
    "subaru": "Subaru",
    "hyundai": "Hyundai",
    "kia": "Kia",
    "bmw": "BMW",
    "vw": "VW",
    "audi": "Audi",
    "fiat": "Fiat",
    "mopar": "Mopar",
    "jlr": "JLR",
    "stellantis": "Stellantis",
    "mitsubishi": "Mitsubishi",
    "ilsac": "ILSAC",
}


def _fmt_visc(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.strip().lower().replace(" ", "")
    m = re.match(r"^(\d{1,2})w(\d{1,2})$", v)
    if m:
        return f"{m.group(1)}W-{m.group(2)}"
    return v.upper()


def _brand(token: Optional[str]) -> str:
    if not token:
        return ""
    t = token.strip().lower()
    return _BRAND_LABELS.get(t, token.strip().title())


def oil_spec_label_for_key(oil_spec_key: Optional[str]) -> Optional[str]:
    """Convert internal oil_spec_key strings into human-readable labels."""
    if not oil_spec_key:
        return None

    k = oil_spec_key.strip()
    kl = k.lower()

    if kl.startswith("tbd_verify"):
        return "TBD (needs verification)"

    # dexos patterns
    m = re.match(r"^dexos1_gen(\d+)_(\d+w\d+)$", kl)
    if m:
        return f"dexos1 Gen {m.group(1)} • {_fmt_visc(m.group(2))}"
    m = re.match(r"^dexos_d_(\d+w\d+)$", kl)
    if m:
        return f"dexosD • {_fmt_visc(m.group(1))}"

    # ILSAC patterns
    m = re.match(r"^ilsac_gf(\d+)([a-z])?_(\d+w\d+)$", kl)
    if m:
        gf = f"GF-{m.group(1)}" + (m.group(2).upper() if m.group(2) else "")
        return f"ILSAC {gf} • {_fmt_visc(m.group(3))}"

    # Ford WSS patterns (example: ford_wss_m2c946_b1_5w30)
    if kl.startswith("ford_wss_"):
        toks = k.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        spec = "-".join(
            [t.upper() if t.lower().startswith("m2c") else t.upper() for t in toks[2:-1]]
        )
        return f"Ford WSS-{spec} • {visc}" if visc else f"Ford WSS-{spec}"

    # Mopar MS patterns (example: ms_6395_5w20)
    m = re.match(r"^ms_(\d+)(?:_(\d+w\d+))?$", kl)
    if m:
        visc = _fmt_visc(m.group(2)) if m.group(2) else None
        return f"Mopar MS-{m.group(1)} • {visc}" if visc else f"Mopar MS-{m.group(1)}"

    # GM older spec patterns (example: gm_6094m_5w30)
    m = re.match(r"^gm_(\w+)_(\d+w\d+)$", kl)
    if m:
        return f"GM {m.group(1).upper()} • {_fmt_visc(m.group(2))}"

    # BMW Longlife patterns (example: bmw_ll17fe_plus_0w20)
    if kl.startswith("bmw_ll"):
        toks = kl.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        ll_base = toks[1].upper().replace("LL", "Longlife-")
        if "plus" in toks:
            ll_base = ll_base + " FE+"
        return f"BMW {ll_base} • {visc}" if visc else f"BMW {ll_base}"

    # VW patterns (example: vw_508_509_0w20)
    if kl.startswith("vw_"):
        toks = kl.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        nums = toks[1:-1]
        if len(nums) >= 2 and nums[0].isdigit() and nums[1].isdigit():
            spec = f"VW {nums[0]} 00 / {nums[1]} 00"
        else:
            spec = "VW " + " ".join([n.upper() for n in nums])
        return f"{spec} • {visc}" if visc else spec

    # Generic pattern: <brand>_..._<visc>_generic
    if kl.endswith("_generic"):
        core = k[:-8]  # strip "_generic"
        toks = core.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        brand = _brand(toks[0]) if toks else ""
        extra = " ".join([t.upper() for t in toks[1:-1]]).strip()
        if extra:
            return f"{brand} {extra} • {visc}" if visc else f"{brand} {extra}"
        return f"{brand} (generic) • {visc}" if visc else f"{brand} (generic)"

    # Fallback: prettify underscores and viscosity
    toks = kl.split("_")
    if toks and re.match(r"^\d+w\d+$", toks[-1]):
        visc = _fmt_visc(toks[-1])
        head = " ".join([t.upper() for t in toks[:-1]])
        return f"{head} • {visc}"
    return k.replace("_", " ").strip()


def resolve_oil_spec_item(spec_item: Optional[Dict[str, Any]], oil_specs_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Augment raw seed spec item with label + verified flag."""
    if spec_item is None:
        return None

    oil_spec_key = spec_item.get("oil_spec_key")
    resolved = dict(spec_item)

    resolved["label"] = oil_spec_label_for_key(oil_spec_key)

    verified_keys = set((oil_specs_doc or {}).get("verified_spec_keys", []) or [])
    resolved["verified"] = bool(oil_spec_key and oil_spec_key in verified_keys)
    resolved["warning"] = None if resolved["verified"] else "Unverified oil spec — confirm in owner's manual or OEM service info."
    return resolved


def reload_all():
    vehicles_doc = load_json(VEHICLES_PATH)
    oil_specs = load_json(OIL_SPECS_PATH)
    oil_capacity = load_json(OIL_CAPACITY_PATH)
    oil_parts = load_json(OIL_PARTS_PATH)
    return vehicles_doc, oil_specs, oil_capacity, oil_parts


@app.get("/health")
def health():
    return {
        "ok": True,
        "paths": {
            "vehicles_json": str(VEHICLES_PATH.resolve()),
            "oil_specs_seed": str(OIL_SPECS_PATH.resolve()),
            "oil_capacity_seed": str(OIL_CAPACITY_PATH.resolve()),
            "oil_change_parts_seed": str(OIL_PARTS_PATH.resolve()),
            "vin_db": str(VIN_DB_PATH.resolve()),
        },
        "endpoints": [
            "/years",
            "/makes?year=YYYY",
            "/models?year=YYYY&make=MAKE",
            "/vehicles/search?year=YYYY&make=MAKE&model=MODEL",
            "/vin/resolve",
            "/oil-change/by-engine?engine_code=ENGINE_CODE",
        ],
    }


@app.get("/years")
def get_years():
    vehicles_doc, _, _, _ = reload_all()
    years = set()
    for v in vehicles_doc.get("vehicles", []):
        y0 = v.get("year_min")
        y1 = v.get("year_max")
        if isinstance(y0, int) and isinstance(y1, int):
            years.update(range(y0, y1 + 1))
    return sorted(years)


@app.get("/makes")
def get_makes(year: int):
    vehicles_doc, _, _, _ = reload_all()

    makes = set()
    for v in vehicles_doc.get("vehicles", []):
        y0 = as_int(v.get("year_min"))
        y1 = as_int(v.get("year_max"))

        if y0 is None or y1 is None:
            continue

        if y0 <= year <= y1:
            m = v.get("make")
            if m:
                makes.add(m)

    return sorted(makes)



@app.get("/models")
def get_models(year: int, make: str):
    vehicles_doc, _, _, _ = reload_all()
    make_n = norm(make)

    models = set()
    for v in vehicles_doc.get("vehicles", []):
        y0 = as_int(v.get("year_min"))
        y1 = as_int(v.get("year_max"))
        if y0 is None or y1 is None:
            continue

        if y0 <= year <= y1 and norm(v.get("make")) == make_n:
            md = v.get("model")
            if md:
                models.add(md)

    return sorted(models)



def _search_impl(year, make, model):
    vehicles_doc, _, _, _ = reload_all()

    make_n = norm(make)
    model_n = norm(model)

    out = []

    for v in vehicles_doc.get("vehicles", []):
        y0 = as_int(v.get("year_min"))
        y1 = as_int(v.get("year_max"))

        if y0 is None or y1 is None:
            continue

        if not (y0 <= year <= y1):
            continue

        if norm(v.get("make")) != make_n:
            continue

        if norm(v.get("model")) != model_n:
            continue

        out.append(v)

    return out



@app.get("/vehicles/search")
def vehicles_search(year: int, make: str, model: str):
    matches = _search_impl(year, make, model)
    vehicle0 = matches[0] if matches else None
    return {
        "query": {"year": year, "make": make, "model": model},
        "count": len(matches),
        "results": matches,
        "vehicles": matches,
        "vehicle": vehicle0,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vin_hash(vin: str) -> str:
    return hashlib.sha256(vin.encode("utf-8")).hexdigest()


def _nhtsa_decode_vin(vin: str) -> Dict[str, Any]:
    if requests is None:
        return {"ok": False, "error": "requests_not_installed"}

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        return {"ok": False, "error": f"nhtsa_request_failed:{type(e).__name__}"}

    results = (payload or {}).get("Results") or []
    row = results[0] if results else {}

    year = row.get("ModelYear") or row.get("Model Year") or row.get("modelyear")
    make = row.get("Make")
    model = row.get("Model")
    trim = row.get("Trim") or row.get("Series") or row.get("Series2")
    engine = row.get("EngineModel") or row.get("Engine Configuration") or row.get("DisplacementL")

    return {
        "ok": True,
        "year": int(year) if str(year).isdigit() else None,
        "make": make.strip() if isinstance(make, str) and make.strip() else None,
        "model": model.strip() if isinstance(model, str) and model.strip() else None,
        "trim": trim.strip() if isinstance(trim, str) and trim.strip() else None,
        "engine": str(engine).strip() if engine is not None and str(engine).strip() else None,
        "raw": row,
    }


def _sqlite_upsert_rollup(signature: str, decoded: Dict[str, Any], status: str, seed_version: Optional[str], app_version: Optional[str]):
    # IMPORTANT: We do NOT store the VIN (raw or hash) in SQLite.
    now = _utc_now_iso()

    # Ensure folder exists (prevents "unable to open database file")
    VIN_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(VIN_DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vin_resolution_events (
                signature TEXT PRIMARY KEY,
                year INTEGER,
                make TEXT,
                model TEXT,
                trim TEXT,
                engine TEXT,
                resolution_status TEXT,
                count INTEGER,
                first_seen_at TEXT,
                last_seen_at TEXT,
                seed_version TEXT,
                app_version TEXT
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vin_confirmed_mappings (
                signature TEXT PRIMARY KEY,
                confirmed_vehicle_id TEXT,
                confirmed_engine_code TEXT,
                count INTEGER,
                last_seen_at TEXT
            )"""
        )

        cur.execute(
            """UPDATE vin_resolution_events
               SET count = COALESCE(count, 0) + 1,
                   last_seen_at = ?,
                   resolution_status = ?,
                   seed_version = COALESCE(?, seed_version),
                   app_version = COALESCE(?, app_version)
               WHERE signature = ?""",
            (now, status, seed_version, app_version, signature),
        )
        if cur.rowcount == 0:
            cur.execute(
                """INSERT INTO vin_resolution_events
                   (signature, year, make, model, trim, engine, resolution_status, count, first_seen_at, last_seen_at, seed_version, app_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (
                    signature,
                    decoded.get("year"),
                    decoded.get("make"),
                    decoded.get("model"),
                    decoded.get("trim"),
                    decoded.get("engine"),
                    status,
                    now,
                    now,
                    seed_version,
                    app_version,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _signature_for(decoded: Dict[str, Any]) -> str:
    return f"{decoded.get('year')}|{decoded.get('make')}|{decoded.get('model')}|{decoded.get('trim')}|{decoded.get('engine')}"


@app.post("/vin/resolve")
def vin_resolve(payload: Dict[str, Any] = Body(...)):
    vin = str(payload.get("vin", "")).strip().upper()
    seed_version = payload.get("seed_version")
    app_version = payload.get("app_version")

    if not vin:
        return {"status": "ERROR", "error": "VIN_REQUIRED"}

    vin_hash = _vin_hash(vin)

    decoded = _nhtsa_decode_vin(vin)
    if not decoded.get("ok"):
        return {"status": "ERROR", "error": decoded.get("error", "DECODE_FAILED")}

    year = decoded.get("year")
    make = decoded.get("make")
    model = decoded.get("model")

    signature = _signature_for(decoded)

    # Can't even get year/make/model -> unsupported
    if not (year and make and model):
        _sqlite_upsert_rollup(signature, decoded, "UNSUPPORTED", seed_version, app_version)
        return {
            "status": "UNSUPPORTED",
            "vin_hash": vin_hash,
            "decoded": {"year": year, "make": make, "model": model, "trim": decoded.get("trim"), "engine": decoded.get("engine")},
        }

    matches = _search_impl(year, make, model)

    if not matches:
        _sqlite_upsert_rollup(signature, decoded, "UNSUPPORTED", seed_version, app_version)
        return {
            "status": "UNSUPPORTED",
            "vin_hash": vin_hash,
            "decoded": {"year": year, "make": make, "model": model, "trim": decoded.get("trim"), "engine": decoded.get("engine")},
        }

    if len(matches) > 1:
        _sqlite_upsert_rollup(signature, decoded, "AMBIGUOUS", seed_version, app_version)
        return {
            "status": "AMBIGUOUS",
            "vin_hash": vin_hash,
            "decoded": {"year": year, "make": make, "model": model, "trim": decoded.get("trim"), "engine": decoded.get("engine")},
            "candidates": matches[:3],
        }

    vehicle = matches[0]

    engines = vehicle.get("engines") if isinstance(vehicle, dict) else None
    if isinstance(engines, list) and len(engines) > 1:
        _sqlite_upsert_rollup(signature, decoded, "AMBIGUOUS", seed_version, app_version)

        engine_choices = []
        for e in engines[:3]:
            if isinstance(e, dict):
                engine_choices.append(
                    {
                        "engine_code": e.get("engine_code"),
                        "engine_name": e.get("engine_name") or e.get("name") or e.get("label"),
                        "notes": e.get("notes"),
                    }
                )
        return {
            "status": "AMBIGUOUS",
            "vin_hash": vin_hash,
            "decoded": {"year": year, "make": make, "model": model, "trim": decoded.get("trim"), "engine": decoded.get("engine")},
            "vehicle": vehicle,
            "engine_choices": engine_choices,
        }

    # Resolved: either 0 engines (rare) or 1 engine
    engine_code = None
    if isinstance(engines, list) and len(engines) == 1 and isinstance(engines[0], dict):
        engine_code = engines[0].get("engine_code")

    _sqlite_upsert_rollup(signature, decoded, "RESOLVED", seed_version, app_version)

    return {
        "status": "RESOLVED",
        "vin_hash": vin_hash,
        "decoded": {"year": year, "make": make, "model": model, "trim": decoded.get("trim"), "engine": decoded.get("engine")},
        "vehicle": vehicle,
        "engine_code": engine_code,
    }
# --- end VIN resolve endpoint (STEP 2) ---


# ---------------- Oil change lookup (engine -> spec/capacity/parts) ----------------

def _find_seed_item(items, engine_code_raw: str):
    """Match seed item by exact engine_code OR by raw code (strip prefix before '_')."""
    raw_n = norm(engine_code_raw)
    for it in items:
        ec = it.get("engine_code")
        if not ec:
            continue
        if norm(ec) == raw_n:
            return it
        if norm(seed_to_raw(ec)) == raw_n:
            return it
    return None


@app.get("/oil-change/by-engine")
def oil_change_by_engine(engine_code: str):
    """Return oil spec + capacity + filter info for a single engine code."""
    _, oil_specs, oil_capacity, oil_parts = reload_all()

    spec_item = _find_seed_item(oil_specs.get("items", []), engine_code)
    spec_item_resolved = resolve_oil_spec_item(spec_item, oil_specs)
    cap_item = _find_seed_item(oil_capacity.get("items", []), engine_code)
    parts_item = _find_seed_item(oil_parts.get("items", []), engine_code)

    return {
        "engine_code": engine_code,
        "found": {
            "oil_spec": spec_item is not None,
            "oil_capacity": cap_item is not None,
            "oil_parts": parts_item is not None,
        },
        "oil_spec": spec_item_resolved,
        "oil_capacity": cap_item,
        "oil_parts": parts_item,
    }


@app.get("/oil-change/coverage/missing-engine-codes")
def coverage():
    vehicles_doc, oil_specs, oil_capacity, oil_parts = reload_all()

    vehicle_codes = set()
    for v in vehicles_doc.get("vehicles", []):
        for ec in (v.get("engine_codes") or []):
            if ec:
                vehicle_codes.add(ec)

    spec_codes = {seed_to_raw(i.get("engine_code")) for i in oil_specs.get("items", []) if i.get("engine_code")}
    cap_codes = {seed_to_raw(i.get("engine_code")) for i in oil_capacity.get("items", []) if i.get("engine_code")}
    part_codes = {seed_to_raw(i.get("engine_code")) for i in oil_parts.get("items", []) if i.get("engine_code")}

    present = vehicle_codes & spec_codes & cap_codes & part_codes
    missing = vehicle_codes - present

    return {
        "vehicles_engine_codes": len(vehicle_codes),
        "oil_specs_engine_codes": len(spec_codes),
        "oil_capacity_engine_codes": len(cap_codes),
        "oil_parts_engine_codes": len(part_codes),
        "present_engine_codes": len(present),
        "missing_engine_codes": len(missing),
        "missing_engine_codes_list": sorted(missing),
    }
