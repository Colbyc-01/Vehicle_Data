import json
import os

CHUNK_FOLDER = os.path.dirname(__file__)
CHUNK_FILES = [
    "vehicles_1995_1999.json",
    "vehicles_2000_2004.json",
    "vehicles_2005_2009.json",
    "vehicles_2010_2014.json",
    "vehicles_2015_2019.json",
    "vehicles_2020_2024.json",
]

total_rows = 0
missing_code = 0

for filename in CHUNK_FILES:
    path = os.path.join(CHUNK_FOLDER, filename)
    with open(path, "r", encoding="utf-8") as f:
        chunk = json.load(f)

    for row in chunk:
        total_rows += 1
        if "engine_code" not in row or not isinstance(row["engine_code"], list):
            print(f"❌ Missing or invalid in {filename}: {row['year']} {row['make']} {row['model']}")
            missing_code += 1

print(f"\n✅ Total rows checked: {total_rows}")
print(f"❌ Rows missing engine_code: {missing_code}")