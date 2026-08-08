# CatalogBuilder datasets

This directory is for externally sourced catalog data used by the CatalogBuilder pipeline.

## Rules

- Do not commit proprietary or license-restricted datasets unless redistribution is explicitly permitted.
- Preserve the original source file unchanged under `raw/` when its license allows redistribution.
- Imported records are discovery evidence only until verification passes.
- Record the source URL, license/terms, retrieval date, and any transformations in a sidecar metadata JSON file.
- Keep generated normalized/verified outputs out of source control unless intentionally curated for release.

## Preferred schema

CSV/JSON imports should provide as many of these fields as possible:

- `category`
- `brand`
- `part_number`
- `year`
- `make`
- `model`
- `engine`
- `source`

The importer accepts common aliases for these fields.
