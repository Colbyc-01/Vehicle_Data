from __future__ import annotations
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).with_name(".env"))
from urllib.parse import quote_plus
import math
from appv6 import load_json
from api.data.paths import ENGINE_AIR_FILTER_GROUPS_PATH
from api.core.purchase_links import build_buy_links




def _dedupe_candidates(cands, year=None):
    # cands: list[dict] with make/model/year_min/year_max/vehicle_id
    out = []
    seen = set()
    for c in cands:
        y_min = c.get("year_min")
        y_max = c.get("year_max")
        if year is not None and isinstance(y_min, int) and isinstance(y_max, int):
            if year < y_min or year > y_max:
                continue
        key = (
            str(c.get("make","")).lower().strip(), 
            str(c.get("model","")).lower().strip(),
            str(c.get("engine_label","")).lower().strip()
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out
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

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data" / "canonical"
SEEDS = ROOT / "Maintenance" / "Seeds"

VEHICLES_PATH = DATA / "vehicles.json"
ENGINES_PATH = DATA / "engines.json"

print("ROOT =", ROOT)
print("VEHICLES_PATH =", VEHICLES_PATH)
print("VEHICLES_PATH exists =", VEHICLES_PATH.exists())


OIL_SPECS_PATH = SEEDS / "oil_specs_seed.json"
OIL_CAPACITY_PATH = SEEDS / "oil_capacity_seed.json"
OIL_PARTS_PATH = SEEDS / "oil_change_parts_seed.json"
OIL_PRODUCT_GROUPS_PATH = SEEDS / "oil_product_groups.json"
OIL_FILTER_GROUPS_PATH = SEEDS / "oil_filter_groups.json"

ENGINE_AIR_FILTER_PATH = SEEDS / "engine_air_filter_seed.json"
ENGINE_AIR_FILTER_GROUPS_PATH = SEEDS / "engine_air_filter_groups.json"

CABIN_AIR_FILTER_GROUPS_PATH = SEEDS / "cabin_air_filter_groups.json"   
CABIN_AIR_FILTER_PATH = SEEDS / "cabin_air_filter_seed.json"

SPARK_PLUG_SEED_PATH = SEEDS / "spark_plug_seed.json"
SPARK_PLUG_GROUPS_PATH = SEEDS / "spark_plug_groups.json"

WIPER_GROUP_PATH = SEEDS / "wiper_group.json"
WIPER_SEED_PATH = SEEDS / "wiper_seed.json"
WIPER_MATRIX_PATH = SEEDS / "wiper_matrix.json"

HEADLIGHT_BULBS_PATH = SEEDS / "headlight_bulbs_parts_seed.json"
BATTERY_PARTS_PATH = SEEDS / "battery_parts_seed.json"


def _load_optional(path: Path) -> Dict[str, Any]:
    try:
        return load_json(path)
    except Exception:
        return {"items": []}


def _vehicle_key_base(v: Dict[str, Any]) -> str:
    make = (v.get("make") or "").strip().lower()
    model = (v.get("model") or "").strip().lower()
    return f"{make}_{model}".replace(" ", "_")


def _vehicle_key_from(v: Dict[str, Any], year: Optional[int] = None) -> str:
    """Return a vehicle_key used for maintenance seed lookups.

    Backward compatible base key:
      - <make>_<model>
    Optional year-aware key:
      - <make>_<model>_<year>
    """
    base = _vehicle_key_base(v)
    if isinstance(year, int) and year > 1900:
        return f"{base}_{year}"
    return base


def _find_by_engine(items, engine_code):
    raw = seed_to_raw(engine_code)
    for it in items or []:
        if seed_to_raw(it.get("engine_code")) == raw:
            return it
    return None



def _find_by_vehicle_key(items, vehicle_key, year: Optional[int] = None):
    """Find a seed item by vehicle_key with tolerance for schema differences.

    Supports keys such as:
      - "chevrolet_tahoe"
      - "Chevrolet_Tahoe_None_None" (legacy)
      - "chevrolet_tahoe_2018" (year-specific)
      - "chevrolet_tahoe_2015_2019" (year-range)

    Match order:
      1) exact match (case-insensitive)
      2) prefix tolerance
      3) year-range match when year is available
    """
    vk = (vehicle_key or "").strip().lower()
    if not vk:
        return None

    m_vk = re.match(r"^(?P<base>.+)_(?P<year>\d{4})$", vk)
    vk_base = m_vk.group("base") if m_vk else vk
    vk_year = int(m_vk.group("year")) if m_vk else (year if isinstance(year, int) else None)

    for it in items or []:
        sk = (it.get("vehicle_key") or "").strip().lower()
        if not sk:
            continue

        if sk == vk:
            return it
        if sk.startswith(vk + "_"):
            return it
        if vk.startswith(sk + "_"):
            return it

        m = re.match(r"^(?P<base>.+)_(?P<y0>\d{4})_(?P<y1>\d{4})$", sk)
        if m and vk_year:
            base = m.group("base")
            y0 = int(m.group("y0"))
            y1 = int(m.group("y1"))
            if base == vk_base and y0 <= vk_year <= y1:
                return it

    return None


def _hydrate_engine_air_filter(item: dict) -> dict:
    """Normalize engine air filter payload to the Flutter UI contract.

    UI expects either:
      - item['air_filter'] = {oem:{...}, alternatives:[...]}  (preferred)
      - OR item['items'] with displayable labels

    Supports:
      - inline 'air_filter' objects
      - legacy 'engine_air_filter' list schema (v1-placeholder) by extracting OEM when present
      - optional group indirection: item['engine_air_filter_group'] or item['group_key'] referencing engine_air_filter_groups.json

    Also hydrates buy links on OEM + alternatives using build_buy_links().
    """
    if not isinstance(item, dict):
        return {"items": [], "warning": "not covered"}

    def _attach_buy_links(af: dict) -> dict:
        if not isinstance(af, dict):
            return af
        out_af = json.loads(json.dumps(af))  # deep copy (avoid mutating loaded docs)
        oem = out_af.get("oem")
        if isinstance(oem, dict):
            oem["buy_links"] = build_buy_links(oem)
        alts = out_af.get("alternatives")
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    alt["buy_links"] = build_buy_links(alt)
        return out_af

    # 1) If item already provides air_filter, hydrate buy links and return
    af = item.get("air_filter")
    if isinstance(af, dict):
        out = dict(item)
        out["air_filter"] = _attach_buy_links(af)
        return out

    # 2) Group indirection (optional)
    group_key = item.get("engine_air_filter_group") or item.get("group_key")
    if isinstance(group_key, str) and group_key.strip():
        try:
            groups_doc = load_json(ENGINE_AIR_FILTER_GROUPS_PATH)
            groups = groups_doc.get("groups") if isinstance(groups_doc, dict) else None
            if not isinstance(groups, dict):
                groups = groups_doc
            grp = groups.get(group_key.strip()) if isinstance(groups, dict) else None
            if isinstance(grp, dict):
                out = dict(item)
                out["air_filter"] = _attach_buy_links(grp)
                return out
        except Exception as e:

    # 3) Legacy list schema: try to pull OEM + alternatives if present
            legacy = item.get("engine_air_filter")
    if isinstance(legacy, list) and legacy:
        row0 = legacy[0] if isinstance(legacy[0], dict) else None
        if isinstance(row0, dict):
            oem_brand = row0.get("oem_brand")
            oem_part = row0.get("oem_part_number")
            # If placeholders, don't pretend we have coverage
            if oem_part and str(oem_part).strip().upper() != "TBD":
                out = dict(item)
                out["air_filter"] = _attach_buy_links(
                    {
                        "oem": {"brand": oem_brand, "part_number": oem_part},
                        "alternatives": [],
                    }
                )
                return out

    return item

def _hydrate_spark_plugs(item: dict) -> dict:
    if not isinstance(item, dict):
        return {"items": [], "warning": "not covered"}

    def _attach_buy_links(sp: dict) -> dict:
        out = json.loads(json.dumps(sp))
        primary = out.get("primary")
        if isinstance(primary, dict):
            primary["buy_links"] = build_buy_links(primary)
        alts = out.get("alternatives")
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    alt["buy_links"] = build_buy_links(alt)
        return out

    group_key = item.get("plug_group") or item.get("group_key")
    if isinstance(group_key, str) and group_key.strip():
        try:
            groups_doc = load_json(SPARK_PLUG_GROUPS_PATH)
            groups = groups_doc.get("groups")
            grp = groups.get(group_key.strip()) if isinstance(groups, dict) else None
            if isinstance(grp, dict):
                out = dict(item)
                out["spark_plugs"] = _attach_buy_links(grp)
                return out
        except Exception:
            pass

    out = dict(item)
    out["spark_plugs"] = {"primary": None, "alternatives": [], "spec": {}, "qty_per_engine": None}
    out["warning"] = out.get("warning") or "not covered"
    return out



def _hydrate_cabin_air_filter(item: dict) -> dict:
    """Normalize cabin air filter payload to the Flutter UI contract.

    Supports:
      - inline 'cabin_filter' objects
      - group indirection via item['cabin_filter_group_key'] referencing cabin_air_filter_groups.json
      - buy_links hydration on primary + alternatives using build_buy_links()

    Output (preferred):
      item['cabin_filter'] = {primary:{brand,part_number,buy_links}, alternatives:[...], spec:{filter_type:'cabin'}}
    """
    if not isinstance(item, dict):
        return {"items": [], "warning": "not covered"}

    def _attach_buy_links(cf: dict) -> dict:
        if not isinstance(cf, dict):
            return cf
        out_cf = json.loads(json.dumps(cf))  # deep copy
        primary = out_cf.get("primary") or out_cf.get("oem")  # tolerate alternate naming
        if isinstance(primary, dict):
            primary["buy_links"] = build_buy_links(primary)
            out_cf["oem"] = primary
            out_cf.pop("primary", None)
        alts = out_cf.get("alternatives")
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    alt["buy_links"] = build_buy_links(alt)
        # ensure spec.filter_type
        spec = out_cf.get("spec")
        if not isinstance(spec, dict):
            spec = {}
        if not spec.get("filter_type"):
            spec["filter_type"] = "cabin"
        out_cf["spec"] = spec
        return out_cf

    # 1) Inline cabin_filter present
    cf = item.get("cabin_filter")
    if isinstance(cf, dict):
        out = dict(item)
        out["cabin_filter"] = _attach_buy_links(cf)
        return out

    # 2) Group indirection
    group_key = item.get("cabin_filter_group_key") or item.get("group_key")
    if isinstance(group_key, str) and group_key.strip():
        try:
            groups_doc = load_json(CABIN_AIR_FILTER_GROUPS_PATH)
            groups = groups_doc.get("groups") if isinstance(groups_doc, dict) else None
            if not isinstance(groups, dict):
                groups = groups_doc  # tolerate top-level mapping style
            grp = groups.get(group_key.strip()) if isinstance(groups, dict) else None
            if isinstance(grp, dict):
                out = dict(item)
                out["cabin_filter"] = _attach_buy_links(grp)
                return out
        except Exception:
            pass

    return item

def _resolve_by_selector(group: dict, vin_attrs: dict | None):
    if not isinstance(group, dict):
        return group

    if not vin_attrs:
        return group.get("fallback", group)
    
    selectors = group.get("selectors")
    if not isinstance(selectors, dict):
        return group

    for key, options in selectors.items():
        val = vin_attrs.get(key)
        if val is None:
            continue
        if isinstance(options, dict):
            if val in options:
                return options[val]
            if str(val) in options:
                return options[str(val)]
        if isinstance(options, list) and isinstance(val, (int, float)):
            for option in options:
                if not isinstance(option, dict):
                    continue
                value = option.get("value")
                year_min = option.get("min")
                year_max = option.get("max")
                if (
                    isinstance(value, dict)
                    and isinstance(year_min, int)
                    and isinstance(year_max, int)
                    and year_min <= val <= year_max
                ):
                    return value

    return group.get("fallback", group)

def _hydrate_wiper(seed_item: dict | None, groups_doc: dict, matrix_doc: dict) -> dict:
    if not isinstance(seed_item, dict):
        return {"items": [], "warning": "not covered"}

    group_key = seed_item.get("wiper_group_key")
    groups = (groups_doc or {}).get("groups", {})
    grp = groups.get(group_key) if isinstance(groups, dict) else None
    if not isinstance(grp, dict):
        return {"items": [], "warning": "group not found"}

    matrix = (matrix_doc or {}).get("items", {}) or {}
    out_positions = {}

    for pos_name, pos in (grp.get("positions") or {}).items():
        spec = (pos or {}).get("spec") or {}
        length = spec.get("length_in")
        connector = spec.get("connector_type")
        blade_type = spec.get("blade_type")

        key = f"{length}_{connector}_{blade_type}".lower() if (length and connector and blade_type) else None
        alts = matrix.get(key, []) if key else []

        # --- buy links ---
        oem_out = (pos or {}).get("oem")
        if isinstance(oem_out, dict):
            oem_out = dict(oem_out)

            length = spec.get("length_in")
            connector = spec.get("connector_type")
            blade_type = spec.get("blade_type")

            q = f'{length} inch {blade_type} wiper blade {connector}'.replace("_", " ") if (length and connector and blade_type) else "wiper blade"

            q_encoded = quote_plus(q)

            oem_out["buy_links"] = {
                "amazon": f"https://www.amazon.com/s?k={q_encoded}&tag=SpecLabs-20",
                "ebay": f"https://www.ebay.com/sch/i.html?_nkw={q_encoded}&campid=5339141163",
                "walmart": f"https://www.walmart.com/search/?query={q_encoded}"
            }

        alts_out = []
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    alt_out = dict(alt)
                    if "part_number" not in alt_out and "sku" in alt_out:
                        alt_out["part_number"] = alt_out["sku"]
                    alt_out["buy_links"] = build_buy_links(alt_out)
                    alts_out.append(alt_out)
                else:
                    alts_out.append(alt)
        else:
            alts_out = alts

        out_positions[pos_name] = {
            "oem": oem_out,
            "spec": spec,
            "alternatives": alts_out,
        }

    return {
        "vehicle_key": seed_item.get("vehicle_key"),
        "coverage": seed_item.get("coverage"),
        "wiper_group_key": group_key,
        "positions": out_positions,
    }

from pydantic import BaseModel
from typing import Optional, Dict, Any

class MaintenanceBundleRequest(BaseModel):
    vehicle_id: str
    year: int
    engine_code: Optional[str] = None
    vin_attrs: Optional[Dict[str, Any]] = None

@app.post("/maintenance/bundle")
def maintenance_bundle(req: MaintenanceBundleRequest):
    vehicle_id = req.vehicle_id
    year = req.year
    engine_code = req.engine_code
    vin_attrs = dict(req.vin_attrs or {})
    vin_attrs.setdefault("year", year)
    vehicles_doc, _, oil_specs, oil_capacity, oil_parts, _, _ = reload_all()


    # locate vehicle
    vehicle = None
    for v in vehicles_doc.get("vehicles", []):
        if v.get("vehicle_id") == vehicle_id:
            vehicle = v
            break
    if not vehicle:
        return {"error": "vehicle_id not found"}

    # resolve engine
    chosen_engine = engine_code or (vehicle.get("engine_codes") or [None])[0]

    # oil (reuse existing logic)
    oil = oil_change_by_engine(chosen_engine)

    # load other seeds
    engine_air = _load_optional(ENGINE_AIR_FILTER_PATH)
    cabin = _load_optional(CABIN_AIR_FILTER_PATH)
    wiper_seed = _load_optional(WIPER_SEED_PATH)
    wiper_matrix = _load_optional(WIPER_MATRIX_PATH)    
    wiper_group = _load_optional(WIPER_GROUP_PATH)    
    headlights = _load_optional(HEADLIGHT_BULBS_PATH)
    battery = _load_optional(BATTERY_PARTS_PATH)
    spark_plugs = _load_optional(SPARK_PLUG_SEED_PATH)  

    vkey = _vehicle_key_from(vehicle, year=year)

# ================================
# ENGINE AIR FILTER
# ================================

# 1. Find engine seed entry
    engine_air_item = _find_by_engine(engine_air.get("items", []), chosen_engine)
    engine_air_item = engine_air_item or {"items": [], "warning": "not covered"}

# 2. Hydrate group
    engine_air_item = _hydrate_engine_air_filter(engine_air_item)

# 3. Resolve selector and FLATTEN structure
    if isinstance(engine_air_item, dict) and "air_filter" in engine_air_item:
        resolved = _resolve_by_selector(
            engine_air_item["air_filter"],
            vin_attrs
        )

    # Force flatten to resolved node
        engine_air_item["air_filter"] = resolved

# 4. Re-hydrate so buy_links attach to resolved node
    engine_air_item = _hydrate_engine_air_filter(engine_air_item)

    cabin_item = _find_by_vehicle_key(cabin.get("items", []), vkey, year=year)
    cabin_item = cabin_item or {"items": [], "warning": "not covered"}
    cabin_item = _hydrate_cabin_air_filter(cabin_item)
    cabin_item = _resolve_by_selector(cabin_item, vin_attrs)    
    wiper_item = _find_by_vehicle_key(wiper_seed.get("items", []), vkey, year=year)
    wiper_item = _hydrate_wiper(wiper_item, wiper_group, wiper_matrix) if wiper_item else {"items": [], "warning": "not covered"}
    headlight_item = _find_by_vehicle_key(headlights.get("items", []), vkey, year=year)
    battery_item = _find_by_vehicle_key(battery.get("items", []), vkey, year=year)
    spark_plug_item = _find_by_engine(spark_plugs.get("items", []), chosen_engine)
    spark_plug_item = spark_plug_item or {"items": [], "warning": "not covered"}
    spark_plug_item = _hydrate_spark_plugs(spark_plug_item) 
    vehicle_out = dict(vehicle)
    if isinstance(vin_attrs, dict) and vin_attrs.get("body_style"):
        vehicle_out["body_style"] = vin_attrs["body_style"]

    return {
        "vehicle": vehicle_out,
        "year": year,
        "engine_code": chosen_engine,
        "oil_change": oil,
        "engine_air_filter": engine_air_item or {"items": [], "warning": "not covered"},
        "cabin_air_filter": cabin_item or {"items": [], "warning": "not covered"},
        "wiper": wiper_item or {"items": [], "warning": "not covered"},
        "headlight_bulbs": headlight_item or {"items": [], "warning": "not covered"},
        "battery": battery_item or {"items": [], "warning": "not covered"},
        "spark_plugs": spark_plug_item or {"items": [], "warning": "not covered"},
    }

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

# ---------------- Engine code resolution (alias + disambiguation) ----------------

ENGINE_ALIAS_PATH = DATA / "engine_alias_map.json"
ENGINE_DISAMBIGUATION_PATH = DATA / "engine_disambiguation_map.json"


def load_engine_alias_map() -> Dict[str, str]:
    try:
        with open(ENGINE_ALIAS_PATH, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("engine_alias_map", {}) or {}
    except Exception:
        return {}


def load_engine_disambiguation() -> Dict[str, Any]:
    try:
        with open(ENGINE_DISAMBIGUATION_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f) or {}
            return doc.get("disambiguation", {}) or {}
    except Exception:
        return {}


ENGINE_ALIAS_MAP: Dict[str, str] = load_engine_alias_map()
ENGINE_DISAMBIGUATION: Dict[str, Any] = load_engine_disambiguation()


def _resolve_via_disambiguation(
    raw: str,
    *,
    year: int | None = None,
    make: str | None = None,
    model: str | None = None,
) -> Optional[str]:
    rules = ENGINE_DISAMBIGUATION.get(raw)
    if not rules or not isinstance(rules, list):
        return None

    make_n = norm(make) if make else ""
    model_n = norm(model) if model else ""

    best = None
    best_score = -1

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        # Make (if specified in rule) must match
        rule_make = rule.get("make")
        if rule_make and make_n and norm(rule_make) != make_n:
            continue
        if rule_make and not make_n:
            # can't validate make, treat as non-match
            continue

        # Model (optional) must match if present in rule
        rule_model = rule.get("model")
        if rule_model:
            if not model_n or norm(rule_model) != model_n:
                continue

        # Year range (optional) must contain year if year provided
        y0 = as_int(rule.get("year_min"))
        y1 = as_int(rule.get("year_max"))
        if year is not None and y0 is not None and y1 is not None:
            if not (y0 <= year <= y1):
                continue

        to = rule.get("canonical_engine_code") or rule.get("engine_code_canonical")
        if not to:
            continue

        # Score: prefer model-specific, then tighter year, then make match
        score = 0
        if rule_model:
            score += 10
        if rule_make:
            score += 5
        if year is not None and y0 is not None and y1 is not None:
            span = max(0, y1 - y0)
            score += max(0, 100 - span)  # tighter range wins
        if score > best_score:
            best_score = score
            best = str(to).strip()

    return best


def resolve_engine_code(
    raw: str,
    engine_label: str | None = None,
    *,
    year: int | None = None,
    make: str | None = None,
    model: str | None = None,
) -> str:
    """Resolve a raw engine code to a canonical engine_code used by oil seeds.

    Order:
    1) Disambiguation map (make/year/model context)
    2) Alias map (simple raw -> canonical)
    3) Raw passthrough
    """
    if not raw:
        return raw

    r = str(raw).strip()

    # 1) Disambiguation map
    resolved = _resolve_via_disambiguation(r, year=year, make=make, model=model)
    if resolved:
        return resolved

    # 2) Alias map
    if r in ENGINE_ALIAS_MAP:
        return ENGINE_ALIAS_MAP[r]

    return r



def engine_display_name(engine_code: str, *, vehicle_engine_label: str | None = None, engines_doc: dict | None = None) -> str:
        # 1) Always prefer vehicle-facing label (from vehicles.json)
    if vehicle_engine_label and str(vehicle_engine_label).strip():
        return str(vehicle_engine_label).strip()

    """Return a human-friendly engine label for UI.

    Priority:
      1) engines.json entry engine_name (if present)
      2) compose from engines.json metadata (displacement/config/cyl/aspiration/fuel)
      3) vehicle_engine_label (from vehicles.json) if provided
      4) fallback to engine_code
    """
    if not engine_code:
        return ""
    engines_doc = engines_doc or {}
    e = engines_doc.get(engine_code) or {}

    name = e.get("engine_name")
    if isinstance(name, str) and name.strip():
        # Some engines.json entries accidentally include the engine_code in parentheses,
        # e.g. "Coyote50 (FORD_Coyote50)". Strip that suffix for cleaner UI labels.
        cleaned = name.strip()
        cleaned = re.sub(rf"\s*\(\s*{re.escape(engine_code)}\s*\)\s*$", "", cleaned)
        return cleaned

    # Compose from metadata when available
    disp = e.get("displacement_l")
    cyl = e.get("cylinders")
    config = e.get("configuration")
    asp = e.get("aspiration")
    fuel = e.get("fuel_type")

    parts = []
    if isinstance(disp, (int, float)):
        # avoid 5.699999 -> 5.7
        disp_s = f"{disp:.1f}".rstrip("0").rstrip(".")
        parts.append(f"{disp_s}L")
    if isinstance(asp, str) and asp.strip():
        asp_u = asp.strip().upper()
        if asp_u in {"NA", "N/A"}:
            parts.append("NA")
        else:
            parts.append(asp_u)
    if isinstance(config, str) and config.strip():
        parts.append(config.strip().upper())
    elif isinstance(cyl, int):
        # fallback cylinder-based config
        if cyl == 4:
            parts.append("I4")
        elif cyl == 6:
            parts.append("V6")
        elif cyl == 8:
            parts.append("V8")

    if isinstance(fuel, str) and fuel.strip():
        # normalize common fuels
        fu = fuel.strip()
        if fu.lower() in {"gasoline", "gas"}:
            parts.append("Gas")
        elif fu.lower() in {"diesel"}:
            parts.append("Diesel")
        else:
            parts.append(fu.title())

    composed = " ".join([p for p in parts if p])
    if composed:
        return composed

    if vehicle_engine_label and str(vehicle_engine_label).strip():
        return str(vehicle_engine_label).strip()

    return engine_code
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
        return f"dexos1 Gen {m.group(1)} - {_fmt_visc(m.group(2))}"
    m = re.match(r"^dexos_d_(\d+w\d+)$", kl)
    if m:
        return f"dexosD - {_fmt_visc(m.group(1))}"

    # ILSAC patterns
    m = re.match(r"^ilsac_gf(\d+)([a-z])?_(\d+w\d+)$", kl)
    if m:
        gf = f"GF-{m.group(1)}" + (m.group(2).upper() if m.group(2) else "")
        return f"ILSAC {gf} - {_fmt_visc(m.group(3))}"

    # Ford WSS patterns (example: ford_wss_m2c946_b1_5w30)
    if kl.startswith("ford_wss_"):
        toks = k.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        spec = "-".join(
            [t.upper() if t.lower().startswith("m2c") else t.upper() for t in toks[2:-1]]
        )
        return f"Ford WSS-{spec} - {visc}" if visc else f"Ford WSS-{spec}"

    # Mopar MS patterns (example: ms_6395_5w20)
    m = re.match(r"^ms_(\d+)(?:_(\d+w\d+))?$", kl)
    if m:
        visc = _fmt_visc(m.group(2)) if m.group(2) else None
        return f"Mopar MS-{m.group(1)} - {visc}" if visc else f"Mopar MS-{m.group(1)}"

    # GM older spec patterns (example: gm_6094m_5w30)
    m = re.match(r"^gm_(\w+)_(\d+w\d+)$", kl)
    if m:
        return f"GM {m.group(1).upper()} - {_fmt_visc(m.group(2))}"

    # BMW Longlife patterns (example: bmw_ll17fe_plus_0w20)
    if kl.startswith("bmw_ll"):
        toks = kl.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        ll_base = toks[1].upper().replace("LL", "Longlife-")
        if "plus" in toks:
            ll_base = ll_base + " FE+"
        return f"BMW {ll_base} - {visc}" if visc else f"BMW {ll_base}"

    # VW patterns (example: vw_508_509_0w20)
    if kl.startswith("vw_"):
        toks = kl.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        nums = toks[1:-1]
        if len(nums) >= 2 and nums[0].isdigit() and nums[1].isdigit():
            spec = f"VW {nums[0]} 00 / {nums[1]} 00"
        else:
            spec = "VW " + " ".join([n.upper() for n in nums])
        return f"{spec} - {visc}" if visc else spec

    # Generic pattern: <brand>_..._<visc>_generic
    if kl.endswith("_generic"):
        core = k[:-8]  # strip "_generic"
        toks = core.split("_")
        visc = _fmt_visc(toks[-1]) if toks else None
        brand = _brand(toks[0]) if toks else ""
        extra = " ".join([t.upper() for t in toks[1:-1]]).strip()
        if extra:
            return f"{brand} {extra} - {visc}" if visc else f"{brand} {extra}"
        return f"{brand} (generic) - {visc}" if visc else f"{brand} (generic)"

    # Fallback: prettify underscores and viscosity
    toks = kl.split("_")
    if toks and re.match(r"^\d+w\d+$", toks[-1]):
        visc = _fmt_visc(toks[-1])
        head = " ".join([t.upper() for t in toks[:-1]])
        return f"{head} - {visc}"
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
    resolved["warning"] = None if resolved["verified"] else "Unverified oil spec - confirm in owner's manual or OEM service info."
    return resolved


def reload_all():
    vehicles_doc = load_json(VEHICLES_PATH)
    engines_doc = _load_optional(ENGINES_PATH)
    oil_specs = load_json(OIL_SPECS_PATH)
    oil_capacity = load_json(OIL_CAPACITY_PATH)
    oil_parts = load_json(OIL_PARTS_PATH)
    try:
        oil_filter_groups = load_json(OIL_FILTER_GROUPS_PATH)
    except Exception:
        oil_filter_groups = {}
    try:
        oil_product_groups = load_json(OIL_PRODUCT_GROUPS_PATH)
    except Exception:
        oil_product_groups = {"items": {}}

    # Return a stable 7-tuple for backward compatibility across call sites.
    return vehicles_doc, engines_doc, oil_specs, oil_capacity, oil_parts, oil_filter_groups, oil_product_groups



@app.post("/vin/resolve_and_bundle")
def vin_resolve_and_bundle(payload: Dict[str, Any] = Body(...)):
    """
    Convenience endpoint: resolve VIN and, when possible, return the full maintenance bundle in one call.
    Statuses:
      - READY: bundle present
      - NEEDS_ENGINE_CONFIRMATION: engine_choices present
      - NEEDS_VEHICLE_CONFIRMATION: vehicle_candidates present
      - passthrough: ERROR / UNSUPPORTED
    """
    vin_result = vin_resolve(payload)
    status = vin_result.get("status")

    if status == "RESOLVED":
        vehicle = vin_result.get("vehicle") or {}
        decoded = vin_result.get("decoded") or {}
        engine_code = vin_result.get("engine_code")
        vehicle_id = vehicle.get("vehicle_id")
        year = decoded.get("year")
        vin_attrs = vin_result.get("vin_attrs")
        req = MaintenanceBundleRequest(
            vehicle_id=vehicle.get("vehicle_id"),
            year=year,
            engine_code=engine_code,
            vin_attrs=vin_attrs,
        )
        bundle = maintenance_bundle(req)

        _, engines_doc, _, _, _, _, _ = reload_all()
        engine_name = engine_display_name(engine_code, vehicle_engine_label=vehicle.get("engine_label"), engines_doc=engines_doc)
        return {
            "status": "READY",
            "vin_hash": vin_result.get("vin_hash"),
            "decoded": decoded,
            "vehicle": vehicle,
            "engine_code": engine_code,
            "engine_name": engine_name,
            "bundle": bundle,
        }

    if status == "AMBIGUOUS":
        # vehicle ambiguity (multiple vehicles)
        if vin_result.get("vehicle_candidates"):
            return {
                "status": "NEEDS_VEHICLE_CONFIRMATION",
                "vin_hash": vin_result.get("vin_hash"),
                "decoded": vin_result.get("decoded"),
                "vehicle_candidates": vin_result.get("vehicle_candidates"),
            }
        # engine ambiguity (single vehicle, multiple engines)
        return {
            "status": "NEEDS_ENGINE_CONFIRMATION",
            "vin_hash": vin_result.get("vin_hash"),
            "decoded": vin_result.get("decoded"),
            "vehicle": vin_result.get("vehicle"),
            "engine_choices": vin_result.get("engine_choices"),
            "bundle": None,
        }

    # passthrough for ERROR / UNSUPPORTED (and any other status)
    return {
        "status": status,
        "vin_hash": vin_result.get("vin_hash"),
        "decoded": vin_result.get("decoded"),
        "error": vin_result.get("error"),
        "bundle": None,
    }


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
    vehicles_doc, *_ = reload_all()
    years = set()
    for v in vehicles_doc.get("vehicles", []):
        y0 = v.get("year_min")
        y1 = v.get("year_max")
        if isinstance(y0, int) and isinstance(y1, int):
            years.update(range(y0, y1 + 1))
    return sorted(years)


@app.get("/makes")
def get_makes(year: int):
    vehicles_doc, *_ = reload_all()

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
    vehicles_doc, *_ = reload_all()
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
    vehicles_doc, *_ = reload_all()

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

def _key_alnum(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm(s))


def _fuzzy_model_candidates(year: int, make: str, model: str, limit: int = 8) -> list[dict]:
    """Best-effort catalog match when VIN-decoded model doesn't exactly match canonical model.

    - Handles punctuation/spacing (F150 vs F-150)
    - Handles family names (Silverado -> Silverado 1500/2500HD/3500HD)
    - Returns sorted candidates with a simple score.
    """
    vehicles_doc, *_ = reload_all()

    make_n = norm(make)
    want_norm = norm(model)
    want_key = _key_alnum(model)

    scored: list[tuple[int, dict]] = []

    for v in vehicles_doc.get("vehicles", []):
        y0 = as_int(v.get("year_min"))
        y1 = as_int(v.get("year_max"))
        if y0 is None or y1 is None or not (y0 <= year <= y1):
            continue
        if norm(v.get("make")) != make_n:
            continue

        cand_model = v.get("model") or ""
        cand_norm = norm(cand_model)
        cand_key = _key_alnum(cand_model)

        score = -1
        if cand_norm == want_norm:
            score = 1000
        elif cand_key == want_key and want_key:
            score = 900
        elif cand_norm.startswith(want_norm) and want_norm:
            score = 800
        elif want_norm.startswith(cand_norm) and cand_norm:
            score = 700
        elif want_key and cand_key.startswith(want_key):
            score = 650
        elif want_key and want_key.startswith(cand_key) and cand_key:
            score = 600

        if score < 0:
            continue

        # prefer tighter year ranges
        span = max(0, (y1 - y0))
        score += max(0, 50 - min(50, span))

        scored.append((score, v))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [v for _, v in scored[:limit]]



@app.get("/vehicles/search")
def vehicles_search(year: int, make: str, model: str):
    matches = _search_impl(year, make, model)

    # Normalize engine codes to canonical codes so oil seeds can be queried reliably.
    for v in matches:
        if not isinstance(v, dict):
            continue
        lbl = v.get("engine_label")
        v["engine_codes"] = [
            resolve_engine_code(c, lbl, year=year, make=v.get("make"), model=v.get("model"))
            for c in (v.get("engine_codes") or [])
            if c
        ]

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

    # Engine-related fields (best-effort; varies by VIN / manufacturer)
    displacement_l = row.get("DisplacementL") or row.get("Displacement (L)")
    cylinders = row.get("EngineCylinders") or row.get("Engine Cylinders")
    fuel = row.get("FuelTypePrimary") or row.get("Fuel Type - Primary") or row.get("FuelType")
    eng_model = row.get("EngineModel")
    eng_conf = row.get("EngineConfiguration") or row.get("Engine Configuration")

    def _as_float(x):
        try:
            return float(str(x).strip())
        except Exception:
            return None

    return {
        "ok": True,
        "year": int(year) if str(year).isdigit() else None,
        "make": make.strip() if isinstance(make, str) and make.strip() else None,
        "model": model.strip() if isinstance(model, str) and model.strip() else None,
        "trim": trim.strip() if isinstance(trim, str) and trim.strip() else None,

        # Raw-ish strings for display / debugging
        "engine": (str(eng_model).strip() if eng_model is not None and str(eng_model).strip() else None),

        # Structured engine hints for matching
        "engine_displacement_l": _as_float(displacement_l),
        "engine_cylinders": int(cylinders) if str(cylinders).isdigit() else None,
        "fuel_type": fuel.strip() if isinstance(fuel, str) and fuel.strip() else None,
        "engine_configuration": eng_conf.strip() if isinstance(eng_conf, str) and eng_conf.strip() else None,

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

def _body_style_from_raw(raw):
    v = " ".join([
        str(raw.get("BodyCabType") or ""),
        str(raw.get("BodyClass") or "")
    ]).lower()
    
    # trucks
    if any(k in v for k in ["crew", "double"]):
        return "crew_cab"
    if any(k in v for k in ["extended", "quad", "king", "access", "super"]):
        return "extended_cab"
    if any(k in v for k in ["regular", "standard"]):
        return "regular_cab"

    # suvs / crossovers
    if any(k in v for k in ["suv", "sport utility"]):
        return "suv"
    if "crossover" in v:
        return "crossover"
    
    # cars
    if "sedan" in v:
        return "sedan"
    if "coupe" in v:
        return "coupe"
    if "hatchback" in v:
        return "hatchback"
    if "wagon" in v:
        return "wagon"
    
    # vans
    if any(k in v for k in ["minivan", "van"]):
        return "minivan"

    return None


@app.post("/vin/resolve")
def vin_resolve(payload: Dict[str, Any] = Body(...)):
    vin = str(payload.get("vin", "")).strip().upper()
    seed_version = payload.get("seed_version")
    app_version = payload.get("app_version")

    if not vin:
        return {"status": "ERROR", "error": "VIN_REQUIRED"}

    vin_hash = _vin_hash(vin)

    decoded = _nhtsa_decode_vin(vin)

    vin_attrs = {
    "body_style": _body_style_from_raw(decoded.get("raw", {}))
}
    
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
            "decoded": {
                "year": year,
                "make": make,
                "model": model,
                "trim": decoded.get("trim"),
                "engine": decoded.get("engine"),
                "engine_displacement_l": decoded.get("engine_displacement_l"),
                "engine_cylinders": decoded.get("engine_cylinders"),
                "fuel_type": decoded.get("fuel_type"),
            },
        }

    # 1) Exact match
    matches = _search_impl(year, make, model)

    # 2) Fuzzy match (punctuation + family models)
    if not matches:
        matches = _fuzzy_model_candidates(year, make, model)

    if not matches:
        _sqlite_upsert_rollup(signature, decoded, "UNSUPPORTED", seed_version, app_version)
        return {
            "status": "UNSUPPORTED",
            "vin_hash": vin_hash,
            "decoded": {
                "year": year,
                "make": make,
                "model": model,
                "trim": decoded.get("trim"),
                "engine": decoded.get("engine"),
                "engine_displacement_l": decoded.get("engine_displacement_l"),
                "engine_cylinders": decoded.get("engine_cylinders"),
                "fuel_type": decoded.get("fuel_type"),
            },
        }

    # If multiple possible canonical vehicles, try to auto-pick using VIN engine hints; otherwise ask user to choose.
    if len(matches) > 1:
        # --- AUTO-PICK best vehicle match using VIN engine hints (GLOBAL) ---
        hint_disp = decoded.get("engine_displacement_l")
        hint_engine_model = decoded.get("engine")  # e.g., "L59"

        # 1) If VIN gave an engine model, try map -> canonical engine code and pick a vehicle that contains it.
        hint_engine_code = None
        if hint_engine_model:
            hint_engine_code = resolve_engine_code(
                hint_engine_model,
                None,
                year=year,
                make=make,
                model=model,
            )

        if hint_engine_code:
            by_engine_code = []
            for v in matches:
                if not isinstance(v, dict):
                    continue
                lbl = v.get("engine_label")
                v_eng = [
                    resolve_engine_code(c, lbl, year=year, make=v.get("make"), model=v.get("model"))
                    for c in (v.get("engine_codes") or [])
                    if c
                ]
                if hint_engine_code in v_eng:
                    by_engine_code.append(v)
            if len(by_engine_code) == 1:
                matches = by_engine_code

        # 2) If still multiple, use displacement vs engine_label (e.g., 5.3 matches "5.3L V8")
        if len(matches) > 1 and hint_disp:
            disp_str = str(hint_disp)
            by_disp = [
                v for v in matches
                if isinstance(v, dict) and disp_str in str(v.get("engine_label", ""))
            ]
            if len(by_disp) == 1:
                matches = by_disp
        # --- END AUTO-PICK ---

    # If still multiple possible canonical vehicles, ask user to choose (keep list short)
    if len(matches) > 1:
        _sqlite_upsert_rollup(signature, decoded, "AMBIGUOUS", seed_version, app_version)
        engines_doc = load_json(DATA / "engines.json")
        candidates = []
        for v in matches[:8]:
            if not isinstance(v, dict):
                continue
            # Normalize engine codes for downstream seed lookups
            lbl = v.get("engine_label")
            v_eng = [
                resolve_engine_code(c, lbl, year=year, make=v.get("make"), model=v.get("model"))
                for c in (v.get("engine_codes") or [])
                if c
            ]
            candidates.append(
                {
                    "vehicle_id": v.get("vehicle_id"),
                    "make": v.get("make"),
                    "model": v.get("model"),
                    "year_min": v.get("year_min"),
                    "year_max": v.get("year_max"),
                    "engine_label": v.get("engine_label"),
                    "engine_codes": v_eng,
                    "engine_names": [engine_display_name(ec, vehicle_engine_label=v.get("engine_label"), engines_doc=engines_doc) for ec in v_eng],
                }
            )
        return {
            "status": "AMBIGUOUS",
            "vin_hash": vin_hash,
            "decoded": {
                "year": year,
                "make": make,
                "model": model,
                "trim": decoded.get("trim"),
                "engine": decoded.get("engine"),
                "engine_displacement_l": decoded.get("engine_displacement_l"),
                "engine_cylinders": decoded.get("engine_cylinders"),
                "fuel_type": decoded.get("fuel_type"),
            },
            "vehicle_candidates": _dedupe_candidates(
                candidates, year=decoded.get("year") if isinstance(decoded, dict) else None
            ),
        }

    vehicle = matches[0]

    # Normalize engine codes to canonical codes so seeds can be queried reliably.
    lbl = vehicle.get("engine_label") if isinstance(vehicle, dict) else None
    engine_codes = [
        resolve_engine_code(
            c,
            lbl,
            year=year,
            make=vehicle.get("make") if isinstance(vehicle, dict) else None,
            model=vehicle.get("model") if isinstance(vehicle, dict) else None,
        )
        for c in ((vehicle.get("engine_codes") or []) if isinstance(vehicle, dict) else [])
        if c
    ]

    engines_doc = load_json(DATA / "engines.json")

    # --- Prefer explicit VIN EngineModel (e.g., "L59") when it maps to a canonical code we support ---
    engine_code: Optional[str] = None
    raw_engine_model = decoded.get("engine")
    if raw_engine_model:
        model_hint = resolve_engine_code(
            raw_engine_model,
            lbl,
            year=year,
            make=vehicle.get("make") if isinstance(vehicle, dict) else None,
            model=vehicle.get("model") if isinstance(vehicle, dict) else None,
        )
        if model_hint in engine_codes:
            engine_code = model_hint

    # If not set yet, try to auto-select an engine if VIN decode gives strong hints.
    if engine_code is None:
        hint_disp = decoded.get("engine_displacement_l")
        hint_cyl = decoded.get("engine_cylinders")
        hint_fuel = norm(decoded.get("fuel_type"))

        def _engine_score(code: str) -> int:
            e = engines_doc.get(code) or {}
            score = 0
            if hint_disp is not None and isinstance(e.get("displacement_l"), (int, float)):
                if abs(float(e["displacement_l"]) - float(hint_disp)) <= 0.15:
                    score += 10
            if hint_cyl is not None and as_int(e.get("cylinders")) == hint_cyl:
                score += 7
            if hint_fuel and norm(e.get("fuel_type")) == hint_fuel:
                score += 4
            return score

        if len(engine_codes) == 1:
            engine_code = engine_codes[0]
        elif len(engine_codes) > 1:
            scored = [(_engine_score(c), c) for c in engine_codes]
            scored.sort(reverse=True)
            # Only auto-pick if it's clearly better than the rest
            if scored and scored[0][0] >= 10 and (len(scored) == 1 or scored[0][0] >= scored[1][0] + 5):
                engine_code = scored[0][1]

    # If still ambiguous, return engine choices (with friendly names)
    if len(engine_codes) > 1 and engine_code is None:
        _sqlite_upsert_rollup(signature, decoded, "AMBIGUOUS", seed_version, app_version)
        engine_choices = []
        for c in engine_codes:
            e = engines_doc.get(c) or {}
            engine_choices.append(
                {
                    "engine_code": c,
                    "engine_name": engine_display_name(c, vehicle_engine_label=vehicle.get("engine_label") if isinstance(vehicle, dict) else None, engines_doc=engines_doc),
                    "displacement_l": e.get("displacement_l"),
                    "cylinders": e.get("cylinders"),
                    "fuel_type": e.get("fuel_type"),
                }
            )
        return {
            "status": "AMBIGUOUS",
            "vin_hash": vin_hash,
            "decoded": {
                "year": year,
                "make": make,
                "model": model,
                "trim": decoded.get("trim"),
                "engine": decoded.get("engine"),
                "engine_displacement_l": decoded.get("engine_displacement_l"),
                "engine_cylinders": decoded.get("engine_cylinders"),
                "fuel_type": decoded.get("fuel_type"),
            },
            "vehicle": {
                "vehicle_id": vehicle.get("vehicle_id"),
                "make": vehicle.get("make"),
                "model": vehicle.get("model"),
                "year_min": vehicle.get("year_min"),
                "year_max": vehicle.get("year_max"),
                "engine_label": vehicle.get("engine_label"),
                "engine_codes": engine_codes,
            },
            "engine_choices": engine_choices,
        }

    _sqlite_upsert_rollup(signature, decoded, "RESOLVED", seed_version, app_version)

    return {
        "status": "RESOLVED",
        "vin_hash": vin_hash,
        "decoded": {
            "year": year,
            "make": make,
            "model": model,
            "trim": decoded.get("trim"),
            "engine": decoded.get("engine"),
            "engine_displacement_l": decoded.get("engine_displacement_l"),
            "engine_cylinders": decoded.get("engine_cylinders"),
            "fuel_type": decoded.get("fuel_type"),
        },
        "vehicle": {
            "vehicle_id": vehicle.get("vehicle_id"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "year_min": vehicle.get("year_min"),
            "year_max": vehicle.get("year_max"),
            "engine_label": vehicle.get("engine_label"),
            "engine_codes": engine_codes,
        },
        "engine_code": engine_code,
        "vin_attrs": vin_attrs,
    }

# ---------------- Oil change lookup helpers ----------------

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


def _fallback_oil_spec(resolved_engine_code: str) -> dict:
    # Contract-safe fallback for Flutter (expects oil_spec.label: string)
    return {
        "oil_spec_key": None,
        "label": "Unknown oil spec - check owner's manual",
        "verified": False,
        "warning": f"No oil spec coverage yet for {resolved_engine_code}.",
        "status": "MISSING",
    }


def _fallback_oil_capacity(resolved_engine_code: str) -> dict:
    # Contract-safe fallback for Flutter (expects oil_capacity.capacity_label_with_filter: string)
    return {
        "capacity_quarts_with_filter": None,
        "capacity_label_with_filter": "Unknown capacity - check owner's manual",
        "verified": False,
        "warning": f"No oil capacity coverage yet for {resolved_engine_code}.",
        "status": "MISSING",
    }


def _ensure_capacity_label(cap_item: dict) -> dict:
    """Ensure capacity_label_with_filter is a non-empty string for Flutter contract."""
    out = dict(cap_item) if isinstance(cap_item, dict) else {}
    lbl = out.get("capacity_label_with_filter")

    if isinstance(lbl, str) and lbl.strip():
        return out

    # If variants exist, we can't pick one label reliably; communicate variability
    variants = out.get("variants")
    if isinstance(variants, list) and len(variants) > 0:
        out["capacity_label_with_filter"] = "Varies by configuration"
        return out

    q = out.get("capacity_quarts_with_filter")
    if isinstance(q, (int, float)):
        out["capacity_label_with_filter"] = f"{q:g} qt"
    else:
        out["capacity_label_with_filter"] = "Unknown capacity - check owner's manual"
    return out

@app.get("/oil-change/by-engine")
def oil_change_by_engine(
    engine_code: str,
    year: int | None = None,
    make: str | None = None,
    model: str | None = None,
    engine_label: str | None = None,
):
    """Return oil spec + capacity + filter info for a single engine code.

    Contract notes (Flutter):
      - oil_spec must be an object with a non-empty string field `label`
      - oil_capacity must be an object with a non-empty string field `capacity_label_with_filter`
    """
    _, _, oil_specs, oil_capacity, oil_parts, oil_filter_groups, oil_product_groups = reload_all()

    resolved_engine_code = resolve_engine_code(
        engine_code,
        engine_label,
        year=year,
        make=make,
        model=model,
    )

    spec_item = _find_seed_item(oil_specs.get("items", []), resolved_engine_code)
    spec_item_resolved = resolve_oil_spec_item(spec_item, oil_specs)

    cap_item = _find_seed_item(oil_capacity.get("items", []), resolved_engine_code)
    parts_item = _find_seed_item(oil_parts.get("items", []), resolved_engine_code)

    # --- Oil filter hydration (supports both legacy inline schema and v2 oil_filter_group schema) ---
    oil_filter: Dict[str, Any] = {}
    parts_item_out = parts_item
    if isinstance(parts_item, dict):
        # Prefer new schema: oil_filter_group -> lookup in oil_filter_groups.json
        group_key = parts_item.get("oil_filter_group")
        if isinstance(group_key, str) and group_key.strip() and isinstance(oil_filter_groups, dict):
            grp = oil_filter_groups.get(group_key.strip())
            if isinstance(grp, dict):
                oil_filter = json.loads(json.dumps(grp))  # deep copy (avoid mutating loaded doc)
        # Fallback to legacy inline oil_filter blob
        if not oil_filter:
            legacy = parts_item.get("oil_filter")
            if isinstance(legacy, dict):
                oil_filter = json.loads(json.dumps(legacy))

        # Attach hydrated filter back onto returned parts object (keeps Flutter happy)
        parts_item_out = dict(parts_item)
        if oil_filter:
            parts_item_out["oil_filter"] = oil_filter

    # Add buy links when we have filter data
    oem = oil_filter.get("oem")
    if isinstance(oem, dict):
        oem["buy_links"] = build_buy_links(oem)
    alts = oil_filter.get("alternatives")
    if isinstance(alts, list):
        for alt in alts:
            if isinstance(alt, dict):
                alt["buy_links"] = build_buy_links(alt)
    # Contract-safe fallbacks to prevent Flutter crashes when seeds are missing
    oil_spec_out = spec_item_resolved if isinstance(spec_item_resolved, dict) else _fallback_oil_spec(resolved_engine_code)
    oil_capacity_out = _ensure_capacity_label(cap_item) if isinstance(cap_item, dict) else _fallback_oil_capacity(resolved_engine_code)

    # ---------------- Spec-based oil product groups ----------------

    oil_products = None
    oil_spec_key = oil_spec_out.get("oil_spec_key") if isinstance(oil_spec_out, dict) else None

    if oil_spec_key:
        groups = oil_product_groups.get("items") if isinstance(oil_product_groups, dict) else {}
        oil_products = groups.get(oil_spec_key) if isinstance(groups, dict) else None

    if not oil_products:
        oil_products = {"verified": False, "oem": None, "alternatives": [], "warning": "not covered"}

    # Add buy links to oil products (runtime only; do not store in seed)
    if isinstance(oil_products, dict):
        oil_products = json.loads(json.dumps(oil_products))  # deep copy (avoid mutating loaded doc)

        oem_oil = oil_products.get("oem")
        if isinstance(oem_oil, dict):
            oem_oil["buy_links"] = build_buy_links(oem_oil)

        alt_oils = oil_products.get("alternatives")
        if isinstance(alt_oils, list):
            for alt in alt_oils:
                if isinstance(alt, dict):
                    alt["buy_links"] = build_buy_links(alt)


    purchase_guidance = None
    capacity_qt = oil_capacity_out.get("capacity_quarts_with_filter")

    if isinstance(capacity_qt, (int, float)) and capacity_qt > 0:
        need = float(capacity_qt)
        need_ceil = int(math.ceil(need))

        # Plan A: maximize 5qt, remainder 1qt
        a_5 = need_ceil // 5
        a_1 = need_ceil - (a_5 * 5)
        a_total = a_5 * 5 + a_1
        a_over = a_total - need
        a_count = a_5 + a_1

        # Plan B: all 5qt
        b_5 = int(math.ceil(need_ceil / 5))
        b_total = b_5 * 5
        b_over = b_total - need
        b_count = b_5

        OVERBUY_GUARD_QT = 2.0

        use_b = (b_count < a_count) and ((b_over - a_over) <= OVERBUY_GUARD_QT)

        if use_b:
            suggested = [{"size_qt": 5, "count": b_5}]
            qt_to_buy = b_total
        else:
            suggested = []
            if a_5 > 0:
                suggested.append({"size_qt": 5, "count": a_5})
            if a_1 > 0:
                suggested.append({"size_qt": 1, "count": a_1})
            qt_to_buy = a_total

        purchase_guidance = {
            "qt_needed": need,
            "qt_to_buy": qt_to_buy,   # now equals actual purchased total
            "suggested": suggested
        }


    return {
        "engine_code": engine_code,
        "resolved_engine_code": resolved_engine_code,
        "found": {
            "oil_spec": spec_item is not None,
            "oil_capacity": cap_item is not None,
            "oil_parts": parts_item is not None,
        },
        "oil_spec": oil_spec_out,
        "oil_capacity": oil_capacity_out,
        "oil_parts": parts_item_out,
        "oil_products": oil_products,
        "purchase_guidance": purchase_guidance,
    }


@app.get("/oil-change/coverage/missing-engine-codes")
def coverage():
    vehicles_doc, _, oil_specs, oil_capacity, oil_parts, _, _ = reload_all()

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
