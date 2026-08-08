# AutoSpec CatalogBuilder Next Actions

## Objective

Turn the current source research into a short, actionable acquisition sequence without adding more framework code.

## Immediate work order

1. WIX Filters
   - Confirm exact public fitment lookup entry point.
   - Confirm whether Y/M/M/E can generate engine air filter candidates.
   - Capture terms/caching risk.
   - Record one known-good US vehicle test case and returned part numbers.

2. FRAM
   - Confirm exact public fitment/application entry point.
   - Capture one known-good US vehicle -> engine air filter result.
   - Review commercial-use/caching restrictions.

3. Purolator
   - Confirm vehicle/VIN/part lookup path.
   - Capture one known-good US vehicle -> engine air filter result.
   - Review terms/caching.

4. MANN-FILTER
   - Confirm North American fitment breadth.
   - Capture one known-good US vehicle -> filter result.
   - Review terms/caching.

5. NGK / Niterra
   - Confirm public US Y/M/M/E spark plug lookup.
   - Capture one known-good vehicle result.
   - Review terms/caching.

6. Gates
   - Confirm public US Y/M/M/E belt lookup.
   - Capture one known-good vehicle result.
   - Review terms/caching.

## Evidence required before integration

A source moves from research to implementation only after we have all of the following:

- exact access URL or artifact
- actual US Y/M/M/E -> part-number result
- supported maintenance categories
- access/rate-limit behavior
- commercial-use/caching/redistribution assessment
- candidate-generation vs verification role
- one reproducible known-good vehicle example

## Current first category

Engine air filters remain the first production target because the seed currently has the heaviest placeholder burden and multiple independent filter manufacturers can corroborate fitment.

## Stop conditions

Reject or defer a source if it is:

- taxonomy-only
- vehicle-only with no part fitment
- non-US for the needed coverage
- rate-limited beyond practical use
- monthly-only before AutoSpec has revenue
- unclear/incompatible for commercial caching or redistribution

## Operator workflow

1. Assistant commits source research / acquisition changes to GitHub.
2. Pull locally with `git pull`.
3. Only run tests when code or data-processing logic changes.
4. For documentation/research-only commits, verify the new file(s) exist and continue.
