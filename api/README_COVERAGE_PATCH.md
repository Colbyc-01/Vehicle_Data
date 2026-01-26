# Coverage endpoint patch (Vehicle Data repo layout)

This patch matches your current backend layout:
- Backend file: `api/app.py`
- Seeds: `Maintenance/seeds/*.json`
- Vehicles: `data/canonical/vehicles.json`

## Files in this patch
- `api/app.py`  (your existing file with ONE new endpoint added)

## What changed
Adds:
- `GET /oil-change/coverage/missing-engine-codes`
  - compares engine_codes referenced in vehicles.json to engine_codes present in oil seed files
  - optional: `?include_present=true` includes both sets for debugging

## Install (one step)
1) Backup your current file:
   - `api/app.py` -> `api/app.py.bak`

2) Copy this patch's `api/app.py` into your repo, replacing yours.

3) Run the API and test:
- `/oil-change/coverage/missing-engine-codes`
- `/oil-change/coverage/missing-engine-codes?include_present=true`
