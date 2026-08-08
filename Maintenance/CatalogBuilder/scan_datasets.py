from __future__ import annotations

import argparse
from pathlib import Path

from .dataset_sources import discover_importable_files, source_manifest
from .importers import import_dataset


def scan(root: str | Path) -> int:
    base = Path(root)
    print("Dataset source manifest:")
    for source in source_manifest():
        print(
            f"  {source['name']}: status={source['status']} kind={source['kind']} "
            f"license_required={source['license_required']}"
        )

    files = discover_importable_files(base)
    print(f"\nImportable files: {len(files)}")
    if not files:
        print(f"No CSV/JSON datasets found under: {base}")
        return 0

    total_records = 0
    failures = 0
    for path in files:
        try:
            payload = import_dataset(path)
            count = int(payload.get("record_count", 0))
            total_records += count
            print(f"  OK   {path}  records={count}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL {path}  {exc}")

    print(f"\nImported candidate records: {total_records}")
    print(f"Failed files: {failures}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan a directory for AutoSpec-importable CSV/JSON catalog datasets."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default="Maintenance/CatalogBuilder/datasets/raw",
        help="Directory to scan (default: Maintenance/CatalogBuilder/datasets/raw)",
    )
    args = parser.parse_args()
    return scan(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
