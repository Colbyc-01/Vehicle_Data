# AutoSpec Catalog Builder

The catalog builder bootstraps AutoSpec maintenance fitment data from free/public sources, normalizes candidates into the shared verification model, and keeps paid catalog integrations pluggable for later.

## Pipeline

1. Resolve canonical vehicle identity.
2. Discover candidate parts from one or more sources.
3. Normalize brand/category/part number.
4. Verify fitment with provider application data when available.
5. Export only approved records into canonical maintenance data.

The builder is category-agnostic. Engine air filters are the first target, but the same pipeline is intended for oil filters, cabin filters, spark plugs, belts, brakes, bearings, and other maintenance categories.
