import json
import os

# Path to your master dataset
MASTER_FILE = "vehicles/vehicles.json"

# Output folder (same folder as this script)
OUT_FOLDER = "Vehicle data/vehicle_chunks"

# Define 5-year blocks
BLOCKS = [
    (1995, 1999),
    (2000, 2004),
    (2005, 2009),
    (2010, 2014),
    (2015, 2019),
    (2020, 2024),
]

print("Loading master dataset...")

with open(MASTER_FILE, "r", encoding="utf-8") as f:
    master = json.load(f)

print(f"Loaded {len(master)} total rows")

# Group rows by block
for start, end in BLOCKS:
    block_rows = [
        row for row in master
        if int(row["year"]) >= start and int(row["year"]) <= end
    ]

    filename = f"vehicles_{start}_{end}.json"
    path = os.path.join(OUT_FOLDER, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(block_rows, f, indent=2)

    print(f"✓ Wrote {filename} — {len(block_rows)} rows")