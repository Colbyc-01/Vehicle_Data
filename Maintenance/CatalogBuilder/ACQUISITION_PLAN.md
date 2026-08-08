# AutoSpec Data Acquisition Plan

## Goal

Build a US-market maintenance fitment dataset from multiple independent sources without depending on a recurring paid API.

## Initial integration order

1. WIX Filters — oil, engine air, cabin air, fuel filters
2. FRAM — oil, engine air, cabin air, fuel/transmission filters
3. Purolator — oil, engine air, cabin air, fuel filters
4. NGK / Niterra — spark plugs and ignition
5. Gates — serpentine belts, tensioners, hoses
6. Dayco — independent belt-drive corroboration
7. TRICO / Rain-X / Bosch Wipers — wiper fitment
8. OEM catalogs — OEM part-number corroboration

## Acquisition rules

- Prefer downloadable artifacts, explicit application guides, public structured endpoints, or permissively licensed datasets.
- Preserve raw source files unchanged in `datasets/raw/`.
- Never treat a single source as sufficient verification.
- Separate candidate generation from independent verification.
- Reject non-US, taxonomy-only, or licensing-incompatible sources.
- Do not make AutoSpec production-dependent on rate-limited trial APIs.

## First target

Start with engine air filters because the existing seed has the largest placeholder burden and the filter manufacturers provide multiple independent sources for corroboration.

Target evidence stack:

- Candidate source: WIX / FRAM / Purolator / MANN-FILTER
- Corroboration: at least one independent manufacturer/application source
- OEM evidence when available

## Definition of done for a source

A source is ready for ingestion when all are known:

- exact access URL or artifact
- US-market coverage
- Y/M/M/E-to-part-number capability
- supported categories
- access/rate-limit behavior
- commercial-use/caching/redistribution status
- role: candidate generation, verification, or both
