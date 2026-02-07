from __future__ import annotations
from pathlib import Path

# Paths are computed relative to *this file* so they work no matter the CWD.
BASE = Path(__file__).resolve().parent.parent  # .../api
ROOT = BASE.parent

DATA = ROOT / "data" / "canonical"
SEEDS = ROOT / "Maintenance" / "Seeds"

VEHICLES_PATH = DATA / "vehicles.json"
ENGINES_PATH = DATA / "engines.json"

OIL_SPECS_PATH = SEEDS / "oil_specs_seed.json"
OIL_CAPACITY_PATH = SEEDS / "oil_capacity_seed.json"
OIL_PARTS_PATH = SEEDS / "oil_change_parts_seed.json"
OIL_FILTER_GROUPS_PATH = SEEDS / "oil_filter_groups.json"

ENGINE_AIR_FILTER_PATH = SEEDS / "engine_air_filter_seed.json"
ENGINE_AIR_FILTER_GROUPS_PATH = SEEDS / "engine_air_filter_groups.json"

CABIN_AIR_FILTER_PATH = SEEDS / "cabin_air_filter_seed.json"
CABIN_AIR_FILTER_GROUPS_PATH = SEEDS / "cabin_air_filter_groups.json"

WIPER_BLADES_PATH = SEEDS / "wiper_blades_seed.json"
HEADLIGHT_BULBS_PATH = SEEDS / "headlight_bulbs_parts_seed.json"
BATTERY_PARTS_PATH = SEEDS / "battery_parts_seed.json"

VIN_DB_PATH = ROOT / "Maintenance" / "Data" / "vin_events.db"
