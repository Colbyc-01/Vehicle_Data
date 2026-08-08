#!/usr/bin/env python3
r"""Build and apply high-impact engine air-filter verification batches.

Usage:
  py Maintenance\Utils\air_filter_verifier.py queue
  py Maintenance\Utils\air_filter_verifier.py apply --decisions air_filter_verification_decisions.json --dry-run
  py Maintenance\Utils\air_filter_verifier.py apply --decisions air_filter_verification_decisions.json

The tool never invents fitment data. "apply" only promotes records explicitly
listed in a reviewed decisions file and refuses verified=True with placeholder OEM data.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SEEDS = REPO_ROOT / "Maintenance" / "Seeds"
GROUPS_PATH = SEEDS / "engine_air_filter_groups.json"
SEED_PATH = SEEDS / "engine_air_filter_seed.json"
DEFAULT_QUEUE = REPO_ROOT / "air_filter_verification_queue.json"

PLACEHOLDERS = {"", "tbd", "unknown", "n/a", "na", "none", "verify"}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def norm_brand(value: Any) -> str:
    value = clean(value).lower()
    aliases = {
        "fram": "fram",
        "wix": "wix",
        "purolator": "purolator",
        "mann": "mann",
        "mann-filter": "mann",
        "mahle": "mahle",
        "k&n": "k&n",
        "kn": "k&n",
        "acdelco": "acdelco",
        "ac delco": "acdelco",
    }
    return aliases.get(value, value)


def norm_part(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def part_signature(group: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    parts: set[tuple[str, str]] = set()
    oem = group.get("oem")
    if isinstance(oem, dict):
        brand = norm_brand(oem.get("brand"))
        part = norm_part(oem.get("part_number"))
        if brand and part and brand not in PLACEHOLDERS and part.lower() not in PLACEHOLDERS:
            parts.add((brand, part))
    for alt in group.get("alternatives") or []:
        if not isinstance(alt, dict):
            continue
        brand = norm_brand(alt.get("brand"))
        part = norm_part(alt.get("part_number"))
        if brand and part and brand not in PLACEHOLDERS and part.lower() not in PLACEHOLDERS:
            parts.add((brand, part))
    return tuple(sorted(parts))


def _is_placeholder_group(group: dict[str, Any]) -> bool:
    oem = group.get("oem") if isinstance(group, dict) else None
    if not isinstance(oem, dict):
        return True
    brand = clean(oem.get("brand")).lower()
    part = clean(oem.get("part_number")).lower()
    return brand in PLACEHOLDERS or part in PLACEHOLDERS


def queue(output: Path) -> int:
    groups_doc = load(GROUPS_PATH)
    seed_doc = load(SEED_PATH)
    groups = groups_doc.get("groups", {})
    items = seed_doc.get("items", [])

    engines_by_group: dict[str, list[str]] = defaultdict(list)
    seed_verified: dict[str, bool] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        group_key = clean(item.get("engine_air_filter_group"))
        engine_code = clean(item.get("engine_code"))
        if group_key:
            engines_by_group[group_key].append(engine_code)
            seed_verified[engine_code] = item.get("verified") is True

    families: dict[tuple[tuple[str, str], ...], list[str]] = defaultdict(list)
    standalone: list[str] = []

    for group_key, group in groups.items():
        if not isinstance(group, dict):
            continue
        sig = part_signature(group)
        if sig:
            families[sig].append(group_key)
        else:
            standalone.append(group_key)

    rows = []
    for sig, group_keys in families.items():
        affected_engines = sorted(
            {engine for key in group_keys for engine in engines_by_group.get(key, []) if engine}
        )
        placeholder_groups = 0
        currently_verified_groups = 0
        for key in group_keys:
            group = groups[key]
            if _is_placeholder_group(group):
                placeholder_groups += 1
            oem = group.get("oem") if isinstance(group, dict) else {}
            if isinstance(oem, dict) and oem.get("verified") is True:
                currently_verified_groups += 1

        rows.append(
            {
                "impact": len(affected_engines),
                "group_count": len(group_keys),
                "affected_engines": affected_engines,
                "group_keys": sorted(group_keys),
                "current_part_family": [
                    {"brand": brand, "part_number": part}
                    for brand, part in sig
                ],
                "placeholder_groups": placeholder_groups,
                "currently_verified_groups": currently_verified_groups,
                "verification_mode": (
                    "catalog_first_required"
                    if placeholder_groups or not currently_verified_groups
                    else "audit_existing_verified_family"
                ),
                "seed_candidates_trusted": False,
            }
        )

    rows.sort(key=lambda row: (-row["impact"], -row["group_count"], row["group_keys"][0]))

    result = {
        "contract": "air_filter_verification_queue_v2",
        "source_groups": str(GROUPS_PATH.relative_to(REPO_ROOT)),
        "source_seed": str(SEED_PATH.relative_to(REPO_ROOT)),
        "family_count": len(rows),
        "standalone_no_part_family": len(standalone),
        "policy": {
            "seed_part_families_are_untrusted": True,
            "placeholder_or_unverified_groups_require_catalog_first_verification": True,
            "do_not_promote_existing_part_numbers_without_external_fitment_evidence": True,
        },
        "families": rows,
        "decision_template": {
            "notes": "Create decisions only from external catalog/OEM evidence. Existing seed part numbers are candidates, never proof.",
            "decisions": [
                {
                    "group_keys": ["ENG_AIR_EXAMPLE"],
                    "oem": {
                        "brand": "Example OEM",
                        "part_number": "12345",
                        "verified": True,
                    },
                    "alternatives": [
                        {"brand": "Example", "part_number": "ABC123"}
                    ],
                    "sources": [
                        {
                            "url": "https://example.com/catalog",
                            "type": "manufacturer_or_catalog",
                            "checked": "YYYY-MM-DD",
                        }
                    ],
                }
            ],
        },
    }
    save(output, result)

    print(f"Families: {len(rows)}")
    print(f"Standalone/no usable part family: {len(standalone)}")
    print("Top 10 by affected engines:")
    for row in rows[:10]:
        family = ", ".join(
            f"{p['brand']} {p['part_number']}" for p in row["current_part_family"]
        )
        print(
            f"  impact={row['impact']:>3} groups={row['group_count']:>3} "
            f"placeholders={row['placeholder_groups']:>3} mode={row['verification_mode']} :: {family}"
        )
    print(f"Queue: {output}")
    return 0


def validate_decision(decision: dict[str, Any]) -> None:
    keys = decision.get("group_keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("Each decision requires a non-empty group_keys list")

    oem = decision.get("oem")
    if not isinstance(oem, dict):
        raise ValueError(f"{keys[0]}: decision requires an oem object")

    brand = clean(oem.get("brand"))
    part = clean(oem.get("part_number"))
    verified = oem.get("verified") is True
    if verified and (
        not brand
        or not part
        or brand.lower() in PLACEHOLDERS
        or part.lower() in PLACEHOLDERS
    ):
        raise ValueError(f"{keys[0]}: cannot verify placeholder/empty OEM data")

    sources = decision.get("sources")
    if verified and (not isinstance(sources, list) or not sources):
        raise ValueError(f"{keys[0]}: verified decision requires at least one source")


def apply(decisions_path: Path, dry_run: bool) -> int:
    groups_doc = load(GROUPS_PATH)
    seed_doc = load(SEED_PATH)
    decisions_doc = load(decisions_path)

    groups = groups_doc.get("groups", {})
    items = seed_doc.get("items", [])
    if not isinstance(groups, dict) or not isinstance(items, list):
        raise ValueError("Unexpected air-filter seed/group schema")

    decisions = decisions_doc.get("decisions", [])
    if not isinstance(decisions, list):
        raise ValueError("Decisions file must contain a decisions list")

    items_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if isinstance(item, dict):
            key = clean(item.get("engine_air_filter_group"))
            if key:
                items_by_group[key].append(item)

    changed_groups = 0
    changed_seed_records = 0

    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        validate_decision(decision)

        oem = copy.deepcopy(decision["oem"])
        alternatives = decision.get("alternatives")
        sources = copy.deepcopy(decision.get("sources", []))
        verified = oem.get("verified") is True

        for group_key in decision["group_keys"]:
            if group_key not in groups:
                raise KeyError(f"Unknown group: {group_key}")

            group = groups[group_key]
            group["oem"] = copy.deepcopy(oem)
            if isinstance(alternatives, list):
                group["alternatives"] = copy.deepcopy(alternatives)
            group["verification_sources"] = copy.deepcopy(sources)
            changed_groups += 1

            for seed_item in items_by_group.get(group_key, []):
                if seed_item.get("verified") is not verified:
                    seed_item["verified"] = verified
                    changed_seed_records += 1

    print(f"Groups changed: {changed_groups}")
    print(f"Seed records changed: {changed_seed_records}")

    if dry_run:
        print("Dry run only; no files written.")
        return 0

    save(GROUPS_PATH, groups_doc)
    save(SEED_PATH, seed_doc)
    print(f"Updated: {GROUPS_PATH}")
    print(f"Updated: {SEED_PATH}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("queue", help="Build impact-ranked verification queue")
    q.add_argument("--out", type=Path, default=DEFAULT_QUEUE)

    a = sub.add_parser("apply", help="Apply reviewed verification decisions")
    a.add_argument("--decisions", type=Path, required=True)
    a.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "queue":
        return queue(args.out)
    if args.command == "apply":
        return apply(args.decisions, args.dry_run)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
