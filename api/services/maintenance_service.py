from __future__ import annotations
from typing import Any, Dict, Optional

from api.data.loaders import load_optional, load_json
from api.data.paths import (
    VEHICLES_PATH, ENGINES_PATH,
    ENGINE_AIR_FILTER_PATH, CABIN_AIR_FILTER_PATH,
    WIPER_BLADES_PATH, HEADLIGHT_BULBS_PATH, BATTERY_PARTS_PATH,
)
from api.domain.finders import vehicle_key_from, find_by_engine, find_by_vehicle_key
from api.domain.hydrate_filters import hydrate_engine_air_filter, hydrate_cabin_air_filter

# NOTE: oil_change_by_engine and reload_all are still in your monolith.
# This service is written so you can progressively move oil logic later
# without breaking your current behavior.

def build_maintenance_bundle(
    *,
    reload_all,
    oil_change_by_engine,
    vehicle_id: str,
    year: int,
    engine_code: Optional[str] = None,
) -> Dict[str, Any]:
    vehicles_doc, engines_doc, _, _, _, _, _ = reload_all()

    vehicle = None
    for v in vehicles_doc.get("vehicles", []):
        if v.get("vehicle_id") == vehicle_id:
            vehicle = v
            break
    if not vehicle:
        return {"error": "vehicle_id not found"}

    chosen_engine = engine_code or (vehicle.get("engine_codes") or [None])[0]
    oil = oil_change_by_engine(chosen_engine)

    engine_air = load_optional(ENGINE_AIR_FILTER_PATH)
    cabin = load_optional(CABIN_AIR_FILTER_PATH)
    wipers = load_optional(WIPER_BLADES_PATH)
    headlights = load_optional(HEADLIGHT_BULBS_PATH)
    battery = load_optional(BATTERY_PARTS_PATH)

    vkey = vehicle_key_from(vehicle)

    engine_air_item = find_by_engine(engine_air.get("items", []), chosen_engine) or {"items": [], "warning": "not covered"}
    engine_air_item = hydrate_engine_air_filter(engine_air_item)

    cabin_item = find_by_vehicle_key(cabin.get("items", []), vkey) or {"items": [], "warning": "not covered"}
    cabin_item = hydrate_cabin_air_filter(cabin_item)

    wiper_item = find_by_vehicle_key(wipers.get("items", []), vkey)
    headlight_item = find_by_vehicle_key(headlights.get("items", []), vkey)
    battery_item = find_by_vehicle_key(battery.get("items", []), vkey)

    return {
        "vehicle": vehicle,
        "year": year,
        "engine_code": chosen_engine,
        "oil_change": oil,
        "engine_air_filter": engine_air_item or {"items": [], "warning": "not covered"},
        "cabin_air_filter": cabin_item or {"items": [], "warning": "not covered"},
        "wiper_blades": wiper_item or {"items": [], "warning": "not covered"},
        "headlight_bulbs": headlight_item or {"items": [], "warning": "not covered"},
        "battery": battery_item or {"items": [], "warning": "not covered"},
    }
