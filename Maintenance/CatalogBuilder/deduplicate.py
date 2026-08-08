from __future__ import annotations

from collections import defaultdict

from .normalize import NormalizedCatalogRecord


def deduplicate(records: list[NormalizedCatalogRecord]) -> list[NormalizedCatalogRecord]:
    grouped: dict[tuple[object, ...], list[NormalizedCatalogRecord]] = defaultdict(list)
    for record in records:
        grouped[record.key()].append(record)

    output: list[NormalizedCatalogRecord] = []
    for items in grouped.values():
        best = max(items, key=lambda item: (item.verified, item.confidence, len(item.provenance)))
        provenance: list[str] = []
        metadata = dict(best.metadata)
        verified = False
        confidence = 0.0
        sources: list[str] = []

        for item in items:
            verified = verified or item.verified
            confidence = max(confidence, item.confidence)
            if item.source and item.source not in sources:
                sources.append(item.source)
            for source in item.provenance:
                if source and source not in provenance:
                    provenance.append(source)

        if len(items) > 1:
            metadata["duplicate_record_count"] = len(items)
            metadata["merged_sources"] = sources

        output.append(
            NormalizedCatalogRecord(
                category=best.category,
                brand=best.brand,
                part_number=best.part_number,
                make=best.make,
                model=best.model,
                year_min=best.year_min,
                year_max=best.year_max,
                engine=best.engine,
                source=best.source,
                confidence=confidence,
                verified=verified,
                provenance=tuple(provenance),
                metadata=metadata,
            )
        )

    return sorted(
        output,
        key=lambda item: (
            item.category,
            item.make,
            item.model,
            item.year_min or 0,
            item.engine,
            item.brand,
            item.part_number,
        ),
    )
