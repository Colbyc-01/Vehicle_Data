from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .deduplicate import deduplicate
from .importers import import_dataset
from .normalize import NormalizedCatalogRecord, normalize_record
from .verify_import import verify_records


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_catalog(input_path: str | Path, output_path: str | Path, verify: bool = True) -> dict[str, Any]:
    imported = import_dataset(input_path)
    raw_records = imported.get("records") if isinstance(imported, dict) else []
    normalized: list[NormalizedCatalogRecord] = []
    for item in raw_records if isinstance(raw_records, list) else []:
        if not isinstance(item, dict):
            continue
        record = normalize_record(item)
        if record is not None:
            normalized.append(record)

    deduped = deduplicate(normalized)
    verified = verify_records(deduped) if verify else deduped

    payload = {
        "contract": "catalog_builder_output_v1",
        "source_file": str(input_path),
        "imported_record_count": len(raw_records) if isinstance(raw_records, list) else 0,
        "normalized_record_count": len(normalized),
        "deduplicated_record_count": len(deduped),
        "verification_enabled": bool(verify),
        "verified_record_count": sum(1 for record in verified if record.verified),
        "records_with_provider_evidence": sum(
            1
            for record in verified
            if any(str(source).endswith("_application_lookup") for source in record.provenance)
        ),
        "records": [record.to_dict() for record in verified],
    }
    _save(Path(output_path), payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import, normalize, deduplicate, and verify an AutoSpec parts catalog dataset.")
    parser.add_argument("input", type=Path, help="CSV or JSON dataset to import")
    parser.add_argument("-o", "--output", type=Path, default=Path("catalog_builder_output.json"), help="Output JSON path")
    parser.add_argument("--no-verify", action="store_true", help="Skip provider application lookups")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_catalog(args.input, args.output, verify=not args.no_verify)
    print(f"Imported: {payload['imported_record_count']}")
    print(f"Normalized: {payload['normalized_record_count']}")
    print(f"Deduplicated: {payload['deduplicated_record_count']}")
    print(f"Provider evidence: {payload['records_with_provider_evidence']}")
    print(f"Verified: {payload['verified_record_count']}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
