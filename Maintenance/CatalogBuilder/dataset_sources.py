from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetSource:
    name: str
    kind: str
    status: str
    license_required: bool
    notes: str


DATASET_SOURCES: tuple[DatasetSource, ...] = (
    DatasetSource(
        name="local_csv_json",
        kind="file_import",
        status="ready",
        license_required=False,
        notes="Use for legitimately obtained CSV/JSON fitment exports; imported records remain unverified until provider checks pass.",
    ),
    DatasetSource(
        name="manufacturer_export",
        kind="file_import",
        status="ready",
        license_required=True,
        notes="Use only when redistribution/usage rights permit AutoSpec ingestion.",
    ),
    DatasetSource(
        name="autocare_aces_pies",
        kind="commercial_dataset",
        status="future",
        license_required=True,
        notes="Architecture-compatible future source; not required for MVP.",
    ),
)


def source_manifest() -> list[dict[str, object]]:
    return [asdict(source) for source in DATASET_SOURCES]


def discover_importable_files(root: str | Path) -> list[Path]:
    base = Path(root)
    if not base.exists():
        return []
    return sorted(
        path
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".json"}
    )
