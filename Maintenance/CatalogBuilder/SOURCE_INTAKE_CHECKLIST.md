# AutoSpec Source Intake Checklist

Complete this checklist before any new external fitment source is ingested.

## Identity

- Source name
- Publisher / owner
- Source URL
- Access date
- Artifact or endpoint type
- US-market scope confirmed

## Fitment capability

- Year
- Make
- Model
- Engine / trim discriminator
- Exact manufacturer or aftermarket part number
- Category coverage
- OE cross-reference availability
- Competitive cross-reference availability

## Access behavior

- Public download, documented API, public HTML, or authenticated access
- Rate limit observed
- Anti-bot behavior observed
- Stable identifiers/endpoints
- Bulk export available
- Pagination / result cap documented

## Rights review

- Terms/license URL recorded
- Commercial use allowed or unresolved
- Local caching allowed or unresolved
- Redistribution in consumer application allowed or unresolved
- Attribution requirements recorded
- Raw artifact redistribution allowed or prohibited

## Pipeline decision

- Candidate generation
- Independent verification
- Both
- Reject / defer

## Acceptance gate

Do not ingest into production data unless:

1. The source exposes actual vehicle-to-part relationships.
2. US-market coverage is adequate for the intended category.
3. Exact part numbers are present.
4. Access is stable enough to reproduce evidence.
5. Rights are sufficiently clear for the intended use.
6. A second independent source can corroborate fitment before promotion to verified.
