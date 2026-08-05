#!/usr/bin/env python3
"""Read-only audit for AutoSpec maintenance seed data."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
SEEDS_DIR = REPO_ROOT / "Maintenance" / "Seeds"
DEFAULT_REPORT = REPO_ROOT / "maintenance_data_audit_report.json"
PLACEHOLDERS = {"", "tbd", "unknown", "n/a", "na", "none", "verify"}


@dataclass(frozen=True)
class Category:
    name: str
    seed_file: str
    identity: str
    group_fields: tuple[str, ...] = ()
    group_file: str | None = None
    group_root: str | None = "groups"


CATEGORIES = (
    Category("oil_specs", "oil_specs_seed.json", "engine_code", ("oil_spec_key",), "oil_product_groups.json", "items"),
    Category("oil_capacity", "oil_capacity_seed.json", "engine_code"),
    Category("oil_filters", "oil_change_parts_seed.json", "engine_code", ("oil_filter_group",), "oil_filter_groups.json", None),
    Category("engine_air_filters", "engine_air_filter_seed.json", "engine_code", ("engine_air_filter_group",), "engine_air_filter_groups.json"),
    Category("spark_plugs", "spark_plug_seed.json", "engine_code", ("plug_group",), "spark_plug_groups.json"),
    Category("cabin_air_filters", "cabin_air_filter_seed.json", "vehicle_key", ("cabin_filter_group_key",), "cabin_air_filter_groups.json"),
    Category("wiper_blades", "wiper_seed.json", "vehicle_key", ("wiper_group_key",), "wiper_group.json"),
    Category("batteries", "battery_seed.json", "vehicle_key", ("battery_group_key",), "battery_groups.json"),
    Category("headlight_bulbs", "headlight_bulbs_seed.json", "vehicle_key", ("bulb_group_key",), "headlight_bulbs_groups.json"),
    Category("brake_pads", "brake_pads_seed.json", "vehicle_key", ("front_group", "rear_group"), "brake_pads_groups.json"),
    Category("brake_rotors", "brake_rotors_seed.json", "vehicle_key", ("front_group", "rear_group"), "brake_rotors_groups.json"),
    Category("coolant", "coolant_seed.json", "engine_code", ("coolant_group",), "coolant_groups.json"),
    Category("ignition_coils", "ignition_coils_seed.json", "engine_code", ("coil_group",), "ignition_coils_groups.json"),
    Category("pcv_valves", "pcv_valve_seed.json", "engine_code", ("pcv_group",), "pcv_valve_groups.json"),
    Category("serpentine_belts", "serpentine_belt_seed.json", "engine_code", ("belt_group",), "serpentine_belt_groups.json"),
)
SUPPLEMENTAL_CATEGORIES = (
    "battery_parts",
    "headlight_parts",
    "oil_filter_catalog",
    "wiper_matrix",
)
CATEGORY_NAMES = tuple(category.name for category in CATEGORIES) + SUPPLEMENTAL_CATEGORIES


@dataclass(frozen=True)
class Issue:
    severity: str
    category: str
    code: str
    record: str
    message: str


class Audit:
    def __init__(self, repo_root: Path = REPO_ROOT):
        self.repo_root = repo_root
        self.seeds_dir = repo_root / "Maintenance" / "Seeds"
        self.issues: list[Issue] = []
        self.stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.engines: dict[str, dict[str, Any]] = {}

    def add(self, severity: str, category: str, code: str, record: Any, message: str) -> None:
        self.issues.append(Issue(severity, category, code, str(record or "(missing)"), message))

    @staticmethod
    def load(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def groups(document: dict[str, Any], root: str | None) -> dict[str, Any]:
        value = document if root is None else document.get(root, {})
        return value if isinstance(value, dict) else {}

    def audit_json_files(self) -> None:
        paths = [
            self.repo_root / "data" / "canonical" / "vehicles.json",
            self.repo_root / "data" / "canonical" / "engines.json",
            *sorted(self.seeds_dir.glob("*.json")),
        ]
        for path in paths:
            try:
                self.load(path)
            except (OSError, json.JSONDecodeError) as exc:
                self.add("error", "files", "invalid_json", path.relative_to(self.repo_root), str(exc))

    def audit_category(self, category: Category) -> None:
        path = self.seeds_dir / category.seed_file
        if not path.exists():
            self.add("error", category.name, "missing_seed", category.seed_file, "Seed file does not exist")
            return

        document = self.load(path)
        items = document.get("items", []) if isinstance(document, dict) else []
        if not isinstance(items, list):
            self.add("error", category.name, "invalid_items", category.seed_file, "Top-level items must be a list")
            return

        self.stats[category.name]["records"] = len(items)
        identities = [record_identity(category, item) for item in items if isinstance(item, dict)]
        for identity, count in Counter(value for value in identities if value).items():
            if count > 1:
                self.add("error", category.name, "duplicate_record", identity, f"Appears {count} times")

        group_values: dict[str, Any] = {}
        if category.group_file:
            group_path = self.seeds_dir / category.group_file
            if not group_path.exists():
                self.add("error", category.name, "missing_group_file", category.group_file, "Group file does not exist")
            else:
                group_values = self.groups(self.load(group_path), category.group_root)

        audited_groups: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                self.add("error", category.name, "invalid_record", category.seed_file, "Seed item must be an object")
                continue
            identity = item.get(category.identity)
            if not identity:
                self.add("error", category.name, "missing_identity", category.seed_file, f"Missing {category.identity}")
                continue
            if category.identity == "engine_code" and identity not in self.engines:
                self.add("error", category.name, "unknown_engine", identity, "Engine code is absent from engines.json")

            refs = [item.get(field) for field in category.group_fields if item.get(field)]
            if category.group_fields and not refs:
                self.stats[category.name]["uncovered"] += 1
                continue
            for ref in refs:
                self.stats[category.name]["references"] += 1
                if ref not in group_values:
                    self.add("error", category.name, "missing_group", identity, f"Referenced group {ref!r} does not exist")
                    continue
                if ref not in audited_groups:
                    self.audit_group_parts(category.name, ref, group_values[ref])
                    audited_groups.add(ref)

        self.audit_category_semantics(category, items, group_values)

    def audit_group_parts(self, category: str, group_key: str, group: Any) -> None:
        for node in part_nodes(group):
            brand = clean(node.get("brand") or node.get("oem_brand"))
            part_number = clean(node.get("part_number") or node.get("service_part_number") or node.get("oem_part_number"))
            name = clean(node.get("name") or node.get("label") or node.get("sku"))
            values = {brand.lower(), part_number.lower(), name.lower()} - {""}
            if values & PLACEHOLDERS or any("placeholder" in value for value in values):
                self.add("info", category, "placeholder_part", group_key, "Contains a placeholder product")
            elif not part_number and not name:
                self.add("warning", category, "unsearchable_part", group_key, "Product has neither part number nor descriptive name")

    def audit_category_semantics(self, category: Category, items: list[Any], groups: dict[str, Any]) -> None:
        if category.name == "oil_specs":
            self.audit_oil_specs(items)
        elif category.name == "oil_capacity":
            self.audit_oil_capacity(items)
        elif category.name == "oil_filters":
            self.audit_inline_groups(items, groups, "oil_filter", "oil_filter_group")
        elif category.name == "spark_plugs":
            self.audit_spark_plugs(items, groups)
        elif category.name == "wiper_blades":
            self.audit_wipers(items, groups)
        elif category.name == "batteries":
            self.audit_batteries(items, groups)

    def audit_oil_specs(self, items: list[Any]) -> None:
        gas_markers = ("ilsac", "dexos1", "ms_6395")
        diesel_markers = ("ck4", "cj4", "dexosd")
        for item in items:
            if not isinstance(item, dict):
                continue
            engine_code = item.get("engine_code")
            spec_key = clean(item.get("oil_spec_key")).lower()
            fuel = clean(self.engines.get(engine_code, {}).get("fuel_type")).lower()
            if fuel == "diesel" and any(marker in spec_key for marker in gas_markers):
                self.add("error", "oil_specs", "diesel_gas_oil", engine_code, f"Diesel engine uses gasoline oil family {spec_key!r}")
            if fuel == "gasoline" and any(marker in spec_key for marker in diesel_markers):
                self.add("error", "oil_specs", "gas_diesel_oil", engine_code, f"Gasoline engine uses diesel oil family {spec_key!r}")

    def audit_oil_capacity(self, items: list[Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            engine_code = item.get("engine_code")
            capacity = item.get("capacity_quarts_with_filter")
            engine = self.engines.get(engine_code, {})
            if not isinstance(capacity, (int, float)) or capacity <= 0:
                self.add("warning", "oil_capacity", "missing_capacity", engine_code, "Capacity is missing or non-positive")
                continue
            if capacity < 2 or capacity > 20:
                self.add("warning", "oil_capacity", "capacity_outlier", engine_code, f"Capacity {capacity} qt is outside broad automotive limits")
            displacement = engine.get("displacement_l")
            if clean(engine.get("fuel_type")).lower() == "diesel" and isinstance(displacement, (int, float)) and displacement >= 5 and capacity < 7:
                self.add("warning", "oil_capacity", "large_diesel_low_capacity", engine_code, f"{displacement}L diesel has only {capacity} qt capacity")

    def audit_inline_groups(self, items: list[Any], groups: dict[str, Any], inline_field: str, ref_field: str) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            inline = item.get(inline_field)
            ref = item.get(ref_field)
            if isinstance(inline, dict) and ref in groups and inline != groups[ref]:
                self.add("error", "oil_filters", "inline_group_mismatch", item.get("engine_code"), f"Inline data disagrees with group {ref!r}")

    def audit_spark_plugs(self, items: list[Any], groups: dict[str, Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            engine_code = item.get("engine_code")
            group = groups.get(item.get("plug_group"), {})
            quantity = group.get("qty_per_engine") if isinstance(group, dict) else None
            cylinders = self.engines.get(engine_code, {}).get("cylinders")
            fuel = clean(self.engines.get(engine_code, {}).get("fuel_type")).lower()
            if fuel == "gasoline" and isinstance(cylinders, int) and isinstance(quantity, int) and quantity != cylinders:
                self.add("warning", "spark_plugs", "quantity_mismatch", engine_code, f"{cylinders} cylinders but group specifies {quantity} plugs")

    def audit_wipers(self, items: list[Any], groups: dict[str, Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            group = groups.get(item.get("wiper_group_key"), {})
            positions = group.get("positions", {}) if isinstance(group, dict) else {}
            for position in item.get("required_positions") or []:
                spec = positions.get(position, {}).get("spec", {}) if isinstance(positions, dict) else {}
                if not spec.get("length_in"):
                    self.add("warning", "wiper_blades", "missing_length", item.get("wiper_group_key"), f"{position} has no blade length")

    def audit_batteries(self, items: list[Any], groups: dict[str, Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            group = groups.get(item.get("battery_group_key"), {})
            spec = group.get("spec", {}) if isinstance(group, dict) else {}
            if group and not spec.get("group_size"):
                self.add("warning", "batteries", "missing_group_size", item.get("battery_group_key"), "Battery group size is missing")

    def audit_inline_seed(self, name: str, filename: str, identity_field: str) -> None:
        document = self.load(self.seeds_dir / filename)
        items = document.get("items", []) if isinstance(document, dict) else []
        self.stats[name]["records"] = len(items) if isinstance(items, list) else 0
        if not isinstance(items, list):
            self.add("error", name, "invalid_items", filename, "Top-level items must be a list")
            return
        for item in items:
            if isinstance(item, dict):
                self.audit_group_parts(name, item.get(identity_field) or filename, item)

    def audit_catalog(self, name: str, filename: str) -> None:
        document = self.load(self.seeds_dir / filename)
        items = document.get("items", []) if isinstance(document, dict) else []
        values = list(items.values()) if isinstance(items, dict) else items
        self.stats[name]["records"] = len(values) if isinstance(values, list) else 0
        if not isinstance(values, list):
            self.add("error", name, "invalid_items", filename, "Top-level items must be a list or object")
            return
        for index, item in enumerate(values):
            self.audit_group_parts(name, f"{filename}:{index}", item)

    def run(self) -> dict[str, Any]:
        self.audit_json_files()
        engines_path = self.repo_root / "data" / "canonical" / "engines.json"
        if engines_path.exists():
            engines = self.load(engines_path)
            self.engines = engines if isinstance(engines, dict) else {}
        for category in CATEGORIES:
            self.audit_category(category)
        self.audit_inline_seed("battery_parts", "battery_parts_seed.json", "vehicle_key")
        self.audit_inline_seed("headlight_parts", "headlight_bulbs_parts_seed.json", "vehicle_key")
        self.audit_catalog("oil_filter_catalog", "oil_filter_catalog.json")
        self.audit_catalog("wiper_matrix", "wiper_matrix.json")

        severity_counts = Counter(issue.severity for issue in self.issues)
        category_counts: dict[str, Counter] = defaultdict(Counter)
        for issue in self.issues:
            category_counts[issue.category][issue.severity] += 1
        return {
            "summary": {
                "categories": len(CATEGORY_NAMES),
                "errors": severity_counts["error"],
                "warnings": severity_counts["warning"],
                "info": severity_counts["info"],
            },
            "categories": {
                category_name: {
                    **dict(self.stats[category_name]),
                    **dict(category_counts[category_name]),
                }
                for category_name in CATEGORY_NAMES
            },
            "issues": [asdict(issue) for issue in self.issues],
        }


def clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def record_identity(category: Category, item: dict[str, Any]) -> str:
    identity = clean(item.get(category.identity))
    if category.identity != "vehicle_key":
        return identity
    years = item.get("years")
    if isinstance(years, list):
        year_token = "-".join(str(year) for year in years)
    elif isinstance(years, dict):
        year_token = f"{years.get('min')}-{years.get('max')}"
    else:
        year_token = "all"
    return f"{identity}:{year_token}:{clean(item.get('body_style'))}"


def part_nodes(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        keys = set(value)
        if keys & {"brand", "part_number", "name", "asin", "sku", "oem_brand", "oem_part_number", "service_part_number"}:
            yield value
        for child in value.values():
            yield from part_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from part_nodes(child)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT, help="JSON report path")
    parser.add_argument("--fail-on", choices=("never", "error", "warning"), default="never")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = Audit().run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = report["summary"]
    print(f"Maintenance audit: {summary['categories']} categories")
    print(f"Errors: {summary['errors']}  Warnings: {summary['warnings']}  Info: {summary['info']}")
    for category, counts in report["categories"].items():
        print(
            f"{category}: records={counts.get('records', 0)} "
            f"errors={counts.get('error', 0)} warnings={counts.get('warning', 0)} "
            f"uncovered={counts.get('uncovered', 0)}"
        )
    print(f"Report: {args.out}")

    if args.fail_on == "warning" and (summary["errors"] or summary["warnings"]):
        return 1
    if args.fail_on == "error" and summary["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
