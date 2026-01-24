# Maintenance Coverage Ledger (US-only)

This document tracks maintenance domains, their completion status, and intentionally deferred work.
If something feels missing, check here first.

Last updated: 2026-01-23T12:49:09.947319Z

---

## Oil Change (COMPLETE ✅)

Files:
- oil_change_parts_seed.json — COMPLETE (v1 locked)
- oil_specs_seed.json — COMPLETE (v2 locked)
- oil_capacity_seed.json — COMPLETE (v2 locked)

Notes:
- Engine-code driven
- Tier-1 oil specs locked
- Variant handling implemented where required
- Safe for production use

---

## Wiper Blades (PARTIAL ⚠️)

Files:
- wiper_blades_parts_seed.json — PARTIAL (v2, generation-based)

Coverage:
- ~2015–2024 major US vehicles
- Generation-based year ranges
- Covers majority of daily drivers
- MVP-complete for app functionality

Deferred:
- Backfill 1995–2014 generations
- Add low-volume / niche models
- Validate rear wiper edge cases on older trims

Status:
- Safe to ship
- Not exhaustive by design

---

## Cabin Air Filters (NOT STARTED ⏳)

Files:
- cabin_air_filter_parts_seed.json — EMPTY

Planned:
- Vehicle-based fitment
- Start with same vehicle list as wipers
- High ROI, low complexity

---

## Engine Air Filters (NOT STARTED ⏳)

Files:
- engine_air_filter_parts_seed.json — EMPTY

Planned:
- Vehicle-based fitment
- Shared filters across trims common
- Moderate variation

---

## Headlight Bulbs (NOT STARTED ⏳)

Files:
- headlight_bulb_parts_seed.json — EMPTY

Planned:
- Vehicle + trim + housing dependent
- High edge-case count
- Deferred until after air filters

---

## Batteries (NOT STARTED ⏳)

Files:
- battery_parts_seed.json — EMPTY

Planned:
- Group size / AGM / flooded
- Start-stop considerations
- CCA + reserve capacity
- Warranty workflow implications
- Highest complexity non-oil category

---

## Guiding Rule

Do not block app progress to achieve exhaustive coverage.
Partial coverage is acceptable when explicitly documented here.
