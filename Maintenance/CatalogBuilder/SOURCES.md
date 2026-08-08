# AutoSpec Catalog Data Sources

This file tracks candidate automotive fitment and maintenance-data sources for AutoSpec.

## Current strategy

Prefer multiple independent US-market sources over a single recurring paid API. Sources should be evaluated for:

- actual Year/Make/Model/Engine -> part-number fitment
- maintenance-category relevance
- US coverage
- access method (API, HTML, PDF, CSV, XML, JSON)
- candidate-generation usefulness
- independent-verification usefulness
- commercial-use / caching / redistribution risk
- stability and rate limits

## Current leading candidates

| Priority | Source | Best use | Categories | Notes |
|---|---|---|---|---|
| High | WIX Filters | Candidate + verification | Oil, engine air, cabin air, fuel filters | Strong public application and cross-reference data; terms/caching review still required. |
| High | FRAM | Candidate + verification | Oil, engine air, cabin air, fuel/transmission filters | Public application tables and cross references; discoverability and commercial-use review required. |
| High | Purolator | Candidate + verification | Oil, engine air, cabin air, fuel filters | Vehicle/VIN/part lookup; endpoint/data-shape and terms review required. |
| High | MANN-FILTER | Candidate + verification | Oil, air, cabin, fuel filters | Large application catalog; confirm North American breadth and usage terms. |
| High | NGK / Niterra | Candidate + verification | Spark plugs, ignition | Strong category-specific fitment source to investigate. |
| High | Gates | Candidate + verification | Belts, tensioners, hoses | Strong category-specific vehicle application source to investigate. |
| High | Dayco | Candidate + verification | Belts, tensioners, hoses | Useful independent corroboration for belt-drive components. |
| High | TRICO / Rain-X / Bosch Wipers | Candidate + verification | Wiper blades | Useful independent wiper-fitment sources. |
| Medium/High | Bosch Auto Parts | Verification + candidate | Spark plugs, wipers, filters, other maintenance parts | Good brand-specific fitment evidence; candidate-generation path needs category-by-category validation. |
| Medium/High | OEM catalogs | Verification + OEM candidate | Filters, plugs, belts, batteries, fluids, service parts | High-value evidence when public lookup exposes exact OEM part numbers; access and licensing vary by manufacturer. |

## Sources to treat cautiously

- Retailers such as RockAuto, NAPA, AutoZone, O'Reilly, Advance, and similar sites may be useful for candidate discovery, but scraping/caching rights must be reviewed before ingestion.
- Generic vehicle taxonomies without vehicle-to-part relationships are not fitment sources.
- Free trial APIs with restrictive quotas or unclear US coverage should not become production dependencies.

## Status

Issue #19 is the research source of truth for detailed findings and ranking. This document will be updated only when a source is concrete enough to act on.
