import json
import re

ENGINE_FILE = "C:/Users/colby/Vehicle Data/Engines/engines.json"

# Required schema
REQUIRED_FIELDS = {
    "engine_name": str,
    "engine_family": str,
    "engine_code": list,
    "make": str,
    "displacement_l": (int, float),
    "cylinders": int,
    "valvetrain": str,
    "aspiration": str,
    "fuel_type": str,
    "description": str
}

ALLOWED_KEYS = set(REQUIRED_FIELDS.keys())


# -----------------------------
# NORMALIZATION FUNCTIONS
# -----------------------------

def normalize_valvetrain(value):
    v = value.strip()
    v = v.replace("i-VTEC", "I-VTEC").replace("iVTEC", "I-VTEC")
    v = re.sub(r"\bsohc\b", "SOHC", v, flags=re.IGNORECASE)
    v = re.sub(r"\bdohc\b", "DOHC", v, flags=re.IGNORECASE)
    return v

def normalize_aspiration(value):
    v = value.strip().lower()
    mapping = {
        "turbocharged": "Turbocharged",
        "twin-turbocharged": "Twin-Turbocharged",
        "bi-turbocharged": "Twin-Turbocharged",
        "naturally aspirated": "Naturally Aspirated",
        "supercharged": "Supercharged"
    }
    return mapping.get(v, value)

def normalize_fuel_type(value):
    return "Gasoline" if value.strip().lower() == "gasoline" else value

def normalize_engine_family(value):
    v = value.strip()

    if v.lower().startswith("ea"):
        parts = v.split()
        parts[0] = parts[0].upper()
        if len(parts) > 1:
            parts[1] = parts[1].title()
        return " ".join(parts)

    if v.lower() in ["vr6", "v6", "v8", "v10"]:
        return v.upper()

    if re.match(r"^\d\.\dL", v, re.IGNORECASE):
        parts = v.split()
        parts[0] = parts[0].upper()
        parts[1] = parts[1].upper()
        return " ".join(parts)

    return v.title()


def normalize_engine_code_list(engine):
    if "engine_code" in engine and isinstance(engine["engine_code"], list):
        cleaned = []
        for code in engine["engine_code"]:
            if isinstance(code, str):
                cleaned.append(code.strip().upper())
        engine["engine_code"] = cleaned
    return engine


# -----------------------------
# VALIDATION
# -----------------------------

def check_casing(key, value):
    if key == "engine_name" and value != value.upper():
        return "engine_name must be UPPERCASE"

    if key == "engine_family":
        if not (value.isupper() or value.istitle() or value.startswith("EA")):
            return "engine_family should be UPPERCASE, Title Case, or EA-prefixed"

    if key == "valvetrain" and not value.strip().isupper() and "VTEC" not in value.upper():
        return "valvetrain must be UPPERCASE or contain VTEC"

    if key == "aspiration" and value != value.title():
        return "aspiration must be Title Case"

    if key == "fuel_type" and value != value.title():
        return "fuel_type must be Title Case"

    return None


def validate_engine(key, engine):
    errors = []
    warnings = []

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in engine:
            errors.append(f"Missing field: {field}")
            continue

        value = engine[field]

        if not isinstance(value, expected_type):
            errors.append(f"Field '{field}' has wrong type: expected {expected_type}, got {type(value)}")

        if isinstance(value, list) and len(value) == 0:
            errors.append(f"Field '{field}' is an empty list")

        if value is None:
            errors.append(f"Field '{field}' is null")

        if isinstance(value, str):
            casing_issue = check_casing(field, value)
            if casing_issue:
                errors.append(casing_issue)

    for field in engine.keys():
        if field not in ALLOWED_KEYS:
            warnings.append(f"Unexpected field: {field}")

    if engine["engine_code"]:
        if engine["engine_name"] not in engine["engine_code"]:
            warnings.append("engine_name does not appear in engine_code list")

    disp = engine["displacement_l"]
    cyl = engine["cylinders"]

    if cyl == 4 and disp > 3.0:
        warnings.append("Unusual: 4-cylinder engine with displacement > 3.0L")
    if cyl == 6 and disp < 2.0:
        warnings.append("Unusual: 6-cylinder engine with displacement < 2.0L")
    if cyl == 8 and disp < 3.0:
        warnings.append("Unusual: 8-cylinder engine with displacement < 3.0L")

    desc = engine["description"].lower()
    if str(engine["displacement_l"])[:3] not in desc:
        warnings.append("Description missing displacement")
    if "vtec" in engine["valvetrain"].lower() and "vtec" not in desc:
        warnings.append("Description missing VTEC mention")

    return errors, warnings


# -----------------------------
# MAIN SCRIPT
# -----------------------------

def main():
    print(f"\n🔍 Loading engine data from {ENGINE_FILE}...\n")

    with open(ENGINE_FILE, "r", encoding="utf-8") as f:
        engines = json.load(f)

    changes = []
    issues_found = False
    warnings_found = False

    for key, engine in engines.items():
        original = engine.copy()

        engine["valvetrain"] = normalize_valvetrain(engine["valvetrain"])
        engine["aspiration"] = normalize_aspiration(engine["aspiration"])
        engine["fuel_type"] = normalize_fuel_type(engine["fuel_type"])
        engine["engine_family"] = normalize_engine_family(engine["engine_family"])
        engine = normalize_engine_code_list(engine)

        for field in ["valvetrain", "aspiration", "fuel_type", "engine_family", "engine_code"]:
            if engine[field] != original[field]:
                changes.append(f"{key}: {field} → '{original[field]}' → '{engine[field]}'")

        errors, warns = validate_engine(key, engine)

        if errors:
            issues_found = True
            print(f"❌ Issues in '{key}':")
            for err in errors:
                print(f"   - {err}")
            print()

        if warns:
            warnings_found = True
            print(f"⚠️ Warnings in '{key}':")
            for w in warns:
                print(f"   - {w}")
            print()

    with open(ENGINE_FILE, "w", encoding="utf-8") as f:
        json.dump(engines, f, indent=2, separators=(',', ': '))

    print("\n✅ Normalization complete.")

    if changes:
        print("\n🔧 Auto-fixes applied:")
        for c in changes:
            print(" - " + c)

    if not issues_found:
        print("\n✅ No schema errors found.")

    if not warnings_found:
        print("\n✨ No warnings — everything looks clean!")


if __name__ == "__main__":
    main()