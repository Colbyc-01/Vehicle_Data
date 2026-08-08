from __future__ import annotations

from dataclasses import replace

from Maintenance.Verify.providers.registry import get_provider

from .normalize import NormalizedCatalogRecord


def verify_records(records: list[NormalizedCatalogRecord]) -> list[NormalizedCatalogRecord]:
    output: list[NormalizedCatalogRecord] = []
    for record in records:
        provider_name = record.brand.strip().lower()
        provenance = list(record.provenance)
        metadata = dict(record.metadata)
        verified = record.verified
        confidence = record.confidence

        try:
            provider = get_provider(provider_name)
        except KeyError:
            output.append(record)
            continue

        try:
            applications = provider.applications_for_part(record.part_number)
        except Exception as exc:
            metadata["verification_error"] = str(exc)
            output.append(replace(record, metadata=metadata))
            continue

        metadata["provider_application_count"] = len(applications)
        if applications:
            marker = f"{provider.name.lower()}_application_lookup"
            if marker not in provenance:
                provenance.append(marker)
            confidence = max(confidence, 0.6)

        output.append(
            replace(
                record,
                verified=verified,
                confidence=confidence,
                provenance=tuple(provenance),
                metadata=metadata,
            )
        )
    return output
