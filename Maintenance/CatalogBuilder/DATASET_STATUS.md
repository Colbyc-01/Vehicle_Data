# AutoSpec Dataset Status

This file tracks external automotive fitment/data artifacts as they move through the CatalogBuilder workflow.

## Status definitions

- `RESEARCH` — source identified, artifact not acquired yet
- `RAW` — artifact acquired and stored in `datasets/raw/`
- `IMPORTED` — parsed into normalized CatalogBuilder records
- `VERIFIED` — fitment corroborated by independent evidence/providers
- `REJECTED` — unusable, unsafe, duplicate, non-US, taxonomy-only, licensing issue, or otherwise not suitable

## Current datasets

| Dataset / Source | Category | Status | Location | Notes |
|---|---|---|---|---|
| AutoPartsAPI trial | Multi-category | REJECTED | n/a | US vehicle resolution/rate-limit behavior made it unsuitable as a primary source for now. Keep adapter code for possible future use. |

## Workflow

1. Acquire an allowed/public artifact.
2. Place original untouched file in `datasets/raw/`.
3. Record it in this table.
4. Import/normalize into `datasets/imported/`.
5. Verify vehicle-to-part fitment using independent evidence.
6. Promote verified outputs to `datasets/verified/`.
7. Move unusable test artifacts/results to `datasets/rejected/` when appropriate.

Do not mark a dataset or part fitment verified solely because one source claims it.
