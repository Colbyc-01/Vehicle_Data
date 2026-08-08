# AutoSpec Fitment Research Backlog

This file turns Issue #19 into concrete acquisition work. No code changes are implied by this backlog.

## Tier 1 — verify exact usable access first

1. WIX Filters
   - Goal: confirm exact public Y/M/M/E application path and cross-reference path.
   - Categories: oil, engine air, cabin air, fuel filters.
   - Needed: source URL(s), response/artifact shape, caching/terms status, US coverage notes.

2. FRAM
   - Goal: confirm exact vehicle-to-part application flow and cross-reference access.
   - Categories: oil, engine air, cabin air, fuel/transmission filters.
   - Needed: source URL(s), application table shape, rate-limit/anti-bot behavior, caching/terms status.

3. Purolator
   - Goal: confirm exact Part Finder/VIN/vehicle lookup flow.
   - Categories: oil, engine air, cabin air, fuel filters.
   - Needed: source URL(s), response/artifact shape, commercial-use/caching review.

4. NGK / Niterra
   - Goal: confirm US Y/M/M/E spark-plug lookup and exact part-number output.
   - Categories: spark plugs, ignition.
   - Needed: source URL(s), application output, whether downloadable guides exist, terms status.

5. Gates
   - Goal: confirm public Y/M/M/E application data for belts and related drive components.
   - Categories: serpentine belts, tensioners, hoses.
   - Needed: source URL(s), structured/downloadable artifact if available, terms status.

## Tier 2 — corroboration and category expansion

6. MANN-FILTER — filters, especially independent corroboration.
7. Dayco — belt-drive corroboration.
8. DENSO — spark plugs and wipers where applicable.
9. Bosch Auto Parts — plugs, wipers, filters, other maintenance parts.
10. TRICO / Rain-X / Bosch Wipers — wiper fitment.
11. Interstate / East Penn / Clarios-family tools — battery application data.
12. OEM catalogs — OEM part-number corroboration by manufacturer.

## Acceptance criteria for moving a source to ACTIVE

A source can move from RESEARCH to ACTIVE only when all of the following are documented:

- exact URL or downloadable artifact
- US-market coverage confirmed
- actual vehicle-to-part-number fitment confirmed
- categories covered
- candidate generation vs verification role
- rate-limit/access behavior
- commercial-use/caching/redistribution status understood well enough to proceed

## Rejection criteria

Reject or defer sources that are:

- taxonomy-only
- model-only without part relationships
- non-US for our target use
- monthly-only with no near-term business case
- too rate-limited to support acquisition
- scraping-sensitive with unclear rights
- unable to expose exact part numbers

## Immediate next action

Do not add more generic source names. Work Tier 1 in order and capture concrete URLs/artifacts and rights notes before any new integration code is written.
