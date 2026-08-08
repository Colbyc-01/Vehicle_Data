from __future__ import annotations

import argparse
import json
from pathlib import Path

from .importers import import_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a public parts catalog CSV/JSON into AutoSpec discovery records.")
    parser.add_argument("source", type=Path, help="Input .csv or .json file")
    parser.add_argument("--out", type=Path, default=Path("catalog_import.json"), help="Output JSON file")
    args = parser.parse_args()

    payload = import_dataset(args.source)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Imported records: {payload['record_count']}")
    print(f"Output: {args.out.resolve()}")
    print("All imported records remain discovery-only and unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
