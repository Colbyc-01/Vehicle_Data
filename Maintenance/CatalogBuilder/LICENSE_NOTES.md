# CatalogBuilder License Notes

Purpose: track licensing, redistribution, caching, and commercial-use constraints for every external data source considered by AutoSpec.

## Rules

- Do not treat publicly viewable data as automatically redistributable.
- Record the source URL, publisher, access method, and terms/license before ingesting or caching data.
- Prefer sources with explicit commercial-use rights, downloadable catalogs, permissive licenses, or clear redistribution terms.
- Treat HTML scraping, undocumented endpoints, and retailer pages as high-risk until terms are reviewed.
- Keep candidate-generation evidence separate from verified fitment evidence.
- Do not ship data from a source whose rights are unclear.

## Review Template

| Source | License / Terms | Commercial Use | Caching | Redistribution | Risk | Notes |
|---|---|---:|---:|---:|---|---|
| Example | Explicit license | Yes | Yes | Yes | Low | Replace with real source review |

## Risk Levels

- **Low** — explicit permissive/commercial rights.
- **Medium** — public access but caching/redistribution terms need clarification.
- **High** — scraping-sensitive, retailer-hosted, unclear rights, or terms restrict reuse.
- **Reject** — incompatible license or redistribution prohibited.
