import json

ENGINE_FILE = "C:/Users/colby/Vehicle Data/Engines/engines.json"
SPECS_FILE = "C:/Users/colby/Vehicle Data/Engines/engine_specs.json"
MAINT_FILE = "C:/Users/colby/Vehicle Data/Engines/engine_maintenance.json"

REQUIRED_FIELDS = [
    "engine_name", "engine_family", "engine_code", "make",
    "displacement_l", "cylinders", "valvetrain",
    "aspiration", "fuel_type", "description"
]

def is_valid_engine(entry):
    return isinstance(entry, dict) and all(field in entry for field in REQUIRED_FIELDS)

def split_engines():
    with open(ENGINE_FILE, "r", encoding="utf-8") as f:
        engines = json.load(f)

    specs = {}
    maint = {}

    for key, entry in engines.items():
        if not is_valid_engine(entry):
            print(f"⚠️ Skipping invalid entry: {key}")
            continue

        specs[key] = {
            "engine_name": entry["engine_name"],
            "engine_family": entry["engine_family"],
            "engine_code": entry["engine_code"],
            "make": entry["make"],
            "displacement_l": entry["displacement_l"],
            "cylinders": entry["cylinders"],
            "valvetrain": entry["valvetrain"],
            "aspiration": entry["aspiration"],
            "fuel_type": entry["fuel_type"]
        }

        maint[key] = {
            "engine_name": entry["engine_name"],
            "description": entry["description"]
        }

    with open(SPECS_FILE, "w", encoding="utf-8") as f:
        json.dump(specs, f, indent=2, separators=(',', ': '))

    with open(MAINT_FILE, "w", encoding="utf-8") as f:
        json.dump(maint, f, indent=2, separators=(',', ': '))

    print("\n✅ Split complete. Valid entries written to:")
    print(f" - {SPECS_FILE}")
    print(f" - {MAINT_FILE}")

split_engines()