import json
import sys

# Path to your engines.json
ENGINE_FILE = "C:/Users/colby/Vehicle Data/Engines/engines.json"

# Required fields and their expected types
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

# Allowed keys (no extras)
ALLOWED_KEYS = set(REQUIRED_FIELDS.keys())

# Casing rules
def check_casing(key, value):
    if key == "engine_name" and value != value.upper():
        return "engine_name must be UPPERCASE"
    if key == "engine_family" and value != value.upper() and not value.istitle():
        return "engine_family should be UPPERCASE or Title Case"
    if key == "valvetrain" and value != value.upper():
        return "valvetrain must be UPPERCASE"
    if key == "aspiration" and value != value.title():
        return "aspiration must be Title Case"
    if key == "fuel_type" and value != value.title():
        return "fuel_type must be Title Case"
    return None

def validate_engine(key, engine):
    errors = []

    # Check for missing fields
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in engine:
            errors.append(f"Missing field: {field}")
            continue

        value = engine[field]

        # Type check
        if not isinstance(value, expected_type):
            errors.append(f"Field '{field}' has wrong type: expected {expected_type}, got {type(value)}")

        # Empty list check
        if isinstance(value, list) and len(value) == 0:
            errors.append(f"Field '{field}' is an empty list")

        # Null check
        if value is None:
            errors.append(f"Field '{field}' is null")

        # Casing rules
        if isinstance(value, str):
            casing_issue = check_casing(field, value)
            if casing_issue:
                errors.append(casing_issue)

    # Unexpected keys
    for field in engine.keys():
        if field not in ALLOWED_KEYS:
            errors.append(f"Unexpected field: {field}")

    return errors


def main():
    print(f"Loading engine data from {ENGINE_FILE}...\n")

    with open(ENGINE_FILE, "r", encoding="utf-8") as f:
        engines = json.load(f)

    total = len(engines)
    print(f"Found {total} engines.\n")

    issues_found = False

    for key, engine in engines.items():
        errors = validate_engine(key, engine)
        if errors:
            issues_found = True
            print(f"❌ Issues in '{key}':")
            for err in errors:
                print(f"   - {err}")
            print()

    if not issues_found:
        print("✅ All engines validated successfully — no issues found!")

if __name__ == "__main__":
    main()