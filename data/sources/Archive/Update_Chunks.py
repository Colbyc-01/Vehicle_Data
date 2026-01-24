import json
import os
from Cleaning_Vehicles import VALID

def normalize(s):
    return s.strip().lower() if isinstance(s, str) else s

# --------------------------------------------------
# Allowed schema + Honda cleanup helper
# --------------------------------------------------

ALLOWED_KEYS = {"year", "make", "model", "engine", "engine_code"}

def is_malformed_honda(row):
    if row.get("make", "").lower() != "honda":
        return False
    extra = set(row.keys()) - ALLOWED_KEYS
    return len(extra) > 0

# --------------------------------------------------
# Define your 5-year blocks
# --------------------------------------------------

BLOCKS = [
    (1995, 1999),
    (2000, 2004),
    (2005, 2009),
    (2010, 2014),
    (2015, 2019),
    (2020, 2024),
]

CHUNK_FOLDER = os.path.dirname(__file__)

# --------------------------------------------------
# Process each block file
# --------------------------------------------------

for start, end in BLOCKS:
    filename = f"vehicles_{start}_{end}.json"
    path = os.path.join(CHUNK_FOLDER, filename)

    print(f"\n=== Processing {filename} ===")

    # Load chunk
    with open(path, "r", encoding="utf-8") as f:
        chunk = json.load(f)

    # --------------------------------------------------
    # Remove malformed Honda rows BEFORE anything else
    # --------------------------------------------------
    chunk = [row for row in chunk if not is_malformed_honda(row)]

    # --------------------------------------------------
    # Normalize engine_code for all rows
    # --------------------------------------------------

    for row in chunk:
        if "engine_code" not in row:
            row["engine_code"] = []
        elif not isinstance(row["engine_code"], list):
            row["engine_code"] = [str(row["engine_code"]).strip()]

    # --------------------------------------------------
    # Build VALID keys only for this block
    # --------------------------------------------------

    valid_keys = set()

    for year in range(start, end + 1):
        if year in VALID:
            for make, models in VALID[year].items():
                for model in models:
                    valid_keys.add((year, normalize(make), normalize(model)))

    print(f"  Valid keys for this block: {len(valid_keys)}")

    # --------------------------------------------------
    # Build existing keys from chunk
    # --------------------------------------------------

    existing_keys = {
        (int(row["year"]), normalize(row["make"]), normalize(row["model"]))
        for row in chunk
    }

    print(f"  Existing models in chunk: {len(existing_keys)}")

    kept_rows = []
    removed_rows = []

    # --------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------

    for row in chunk:
        key = (
            int(row["year"]),
            normalize(row["make"]),
            normalize(row["model"])
        )

        if key in valid_keys:
            kept_rows.append(row)
        else:
            removed_rows.append(row)

    # --------------------------------------------------
    # Add missing models (placeholder rows)
    # --------------------------------------------------

    added_rows = []

    for key in valid_keys:
        if key not in existing_keys:
            year, make_norm, model_norm = key

            # Preserve original casing from VALID
            make = None
            model = None

            for m, models in VALID[year].items():
                if normalize(m) == make_norm:
                    make = m
                    for mod in models:
                        if normalize(mod) == model_norm:
                            model = mod
                            break

            added_rows.append({
                "year": year,
                "make": make,
                "model": model,
                "engine": "Unknown",
                "engine_code": []
            })

    # --------------------------------------------------
    # Save updated chunk
    # --------------------------------------------------

    final_rows = kept_rows + added_rows

    with open(path, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=2)

# --------------------------------------------------
# Verification: ensure all VALID keys are present
# --------------------------------------------------

missing_after_update = []

for key in valid_keys:
    if key not in {
        (int(row["year"]), normalize(row["make"]), normalize(row["model"]))
        for row in final_rows
    }:
        missing_after_update.append(key)

if missing_after_update:
    print("  ⚠ Missing after update:")
    for year, make, model in missing_after_update:
        print(f"    - {year} {make} {model}")
else:
    print("  ✓ All VALID makes/models accounted for")
    # --------------------------------------------------
    # Logging
    # --------------------------------------------------

    print(f"  ✓ Updated: {filename}")
    print(f"    ➕ Added rows: {len(added_rows)}")
    print(f"    ➖ Removed rows: {len(removed_rows)}")