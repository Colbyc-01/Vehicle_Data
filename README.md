# Vehicle Data Pipeline

This repository contains a structured pipeline for managing vehicle data,
maintenance definitions, and canonical outputs used for analysis and downstream applications.

## Project Structure

### data/
- `data/sources/`
  - Raw, per-make vehicle source JSON files (Acura, Ford, Toyota, etc.)
  - These files may be incomplete or inconsistent.
- `data/canonical/`
  - Canonical, merged outputs generated from sources
  - `vehicles.json` – unified vehicle list
  - `engines.json` – engine reference data (may be incomplete)

### Maintenance/
Defines the maintenance domain independently of vehicles.

- Core files:
  - `maintenance_items.json` – what maintenance actions exist
  - `maintenance_schedules.json` – intervals (miles / months)
  - `fluids_specs.json` – oil, coolant, brake fluid specs
  - `parts_catalog.json` – part category registry
- `Contracts/` – rules for how maintenance applies
- `Seeds/` – part / spec seed data
- `Targets/` – MVP coverage targets
- `Utils/` – shared helper logic (e.g. engine resolution)

### Scripts/
Utility scripts for building and validating the data:
- `merge_vehicles.py` – merges source files into canonical vehicles
- `analyze_database.py` – audits vehicles and engines for gaps/inconsistencies
- `chunk_vehicles.py`, `sanity_check_aliases.py` – helper tools

## Usage

Create / activate the virtual environment, then run:

```bash
python Scripts/merge_vehicles.py
python Scripts/analyze_database.py

## Notes / Known Gaps

- Engine coverage is incomplete.
  - Some vehicles do not yet have `engine_code` populated.
  - `engines.json` is present but not fully normalized.
- Analysis scripts are used to surface gaps and inconsistencies rather than enforce strict validation.
- Source data varies by make and year and is treated as non-authoritative.

These gaps are expected and are addressed incrementally using analysis output to prioritize work.
