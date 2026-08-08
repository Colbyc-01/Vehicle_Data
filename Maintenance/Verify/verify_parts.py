from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    THIS_DIR = Path(__file__).resolve().parent
    REPO_ROOT = THIS_DIR.parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from Maintenance.Verify.cache import VerificationCache
    from Maintenance.Verify.models import PartRef, SourceHit, VerificationDecision
    from Maintenance.Verify.normalize import normalize_brand, normalize_part_number
    from Maintenance.Verify.providers.registry import get_provider
    from Maintenance.Verify.scoring import auto_approve, score_hits
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    from .cache import VerificationCache
    from .models import PartRef, SourceHit, VerificationDecision
    from .normalize import normalize_brand, normalize_part_number
    from .providers.registry import get_provider
    from .scoring import auto_approve, score_hits

DEFAULT_QUEUE = REPO_ROOT / "air_filter_verification_queue.json"
DEFAULT_OUT = REPO_ROOT / "air_filter_verification_decisions.json"
DEFAULT_WIX_AUDIT = REPO_ROOT / "air_filter_wix_audit.json"
DEFAULT_VEHICLES = REPO_ROOT / "data" / "canonical" / "vehicles.json"
DEFAULT_CACHE = REPO_ROOT / ".cache" / "parts_verification.sqlite3"

MAKE_ALIASES: dict[str, set[str]] = {
    "RAM": {"DODGE"},
    "DODGE": {"RAM"},
    "GENESIS": {"HYUNDAI"},
    "HYUNDAI": {"GENESIS"},
    "GEO": {"CHEVROLET", "SUZUKI"},
    "CHEVROLET": {"GEO", "SUZUKI"},
    "SUZUKI": {"GEO", "CHEVROLET"},
    "EAGLE": {"MITSUBISHI", "CHRYSLER"},
    "MITSUBISHI": {"EAGLE", "CHRYSLER"},
    "PLYMOUTH": {"DODGE", "CHRYSLER"},
    "CHRYSLER": {"PLYMOUTH", "DODGE", "MITSUBISHI"},
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _norm_text(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _tokens(value: Any) -> set[str]:
    text = str(value or "").upper()
    return {token for token in re.findall(r"[A-Z0-9]+", text) if token}


def _make_match(vehicle_make: Any, application_make: Any) -> bool:
    v = _norm_text(vehicle_make)
    a = _norm_text(application_make)
    if not v or not a:
        return True
    if v == a:
        return True
    return a in MAKE_ALIASES.get(v, set()) or v in MAKE_ALIASES.get(a, set())


def _model_match(vehicle_model: Any, application_model: Any) -> bool:
    v = _norm_text(vehicle_model)
    a = _norm_text(application_model)
    if not v or not a:
        return True
    if v == a:
        return True
    if v in a or a in v:
        return True
    vt = _tokens(vehicle_model)
    at = _tokens(application_model)
    return bool(vt and at and vt.issubset(at))


def _engine_displacement(value: Any) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*L\b", str(value or ""), flags=re.I)
    return match.group(1) if match else None


def _engine_match(vehicle_engine: Any, application_engine: Any) -> bool:
    vdisp = _engine_displacement(vehicle_engine)
    adisp = _engine_displacement(application_engine)
    if vdisp and adisp:
        return vdisp == adisp
    return True


def _year_overlap(a0: int | None, a1: int | None, b0: int | None, b1: int | None) -> bool:
    if None in (a0, a1, b0, b1):
        return True
    return max(a0, b0) <= min(a1, b1)


def _vehicle_index(vehicles_path: Path) -> dict[str, list[dict[str, Any]]]:
    doc = load(vehicles_path)
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for vehicle in doc.get("vehicles", []) if isinstance(doc, dict) else []:
        if not isinstance(vehicle, dict):
            continue
        for engine_code in vehicle.get("engine_codes") or []:
            if isinstance(engine_code, str) and engine_code:
                index[engine_code].append(vehicle)
    return index


def _wix_applications(part: str, cache: VerificationCache) -> list[dict[str, Any]]:
    cache_key = f"applications:{part}"
    cached = cache.get("wix", cache_key)
    if cached is not None:
        return cached

    provider = get_provider("wix")
    hits = provider.lookup_part(part)
    applications: list[dict[str, Any]] = []
    for hit in hits:
        metadata = hit.metadata if isinstance(hit.metadata, dict) else {}
        raw = metadata.get("applications")
        if isinstance(raw, list):
            applications.extend(item for item in raw if isinstance(item, dict))

    cache.put("wix", cache_key, applications)
    return applications


def _diagnose_vehicle(vehicle: dict[str, Any], applications: list[dict[str, Any]]) -> dict[str, Any]:
    if not applications:
        return {"reason": "no_applications", "vehicle": vehicle}

    vy0 = vehicle.get("year_min") if isinstance(vehicle.get("year_min"), int) else None
    vy1 = vehicle.get("year_max") if isinstance(vehicle.get("year_max"), int) else None

    make_matches = [app for app in applications if _make_match(vehicle.get("make"), app.get("make"))]
    if not make_matches:
        return {
            "reason": "make_mismatch",
            "vehicle": vehicle,
            "sample_applications": applications[:5],
        }

    model_matches = [app for app in make_matches if _model_match(vehicle.get("model"), app.get("model"))]
    if not model_matches:
        return {
            "reason": "model_mismatch",
            "vehicle": vehicle,
            "same_make_applications": make_matches[:10],
        }

    year_matches = [
        app for app in model_matches
        if _year_overlap(vy0, vy1, app.get("year_min"), app.get("year_max"))
    ]
    if not year_matches:
        return {
            "reason": "year_mismatch",
            "vehicle": vehicle,
            "same_make_model_applications": model_matches[:10],
        }

    engine_matches = [app for app in year_matches if _engine_match(vehicle.get("engine_label"), app.get("engine"))]
    if not engine_matches:
        return {
            "reason": "engine_mismatch",
            "vehicle": vehicle,
            "same_make_model_year_applications": year_matches[:10],
        }

    return {
        "reason": "matched",
        "vehicle": vehicle,
        "matching_applications": engine_matches[:10],
    }


def build_review_decisions(queue_path: Path, out_path: Path, threshold: float) -> int:
    queue = load(queue_path)
    families = queue.get("families", []) if isinstance(queue, dict) else []
    decisions: list[dict[str, Any]] = []

    for family in families:
        if not isinstance(family, dict):
            continue
        current = family.get("current_part_family") or []
        alternatives = tuple(
            PartRef(normalize_brand(item.get("brand")), normalize_part_number(item.get("part_number")))
            for item in current
            if isinstance(item, dict) and item.get("brand") and item.get("part_number")
        )
        hits = tuple(
            SourceHit(
                source=normalize_brand(item.get("brand")) or "unknown",
                query=PartRef(
                    normalize_brand(item.get("brand")) or "unknown",
                    normalize_part_number(item.get("part_number")),
                ),
                matched_part=None,
                confidence=0.0,
                notes="Seed candidate only; not trusted verification evidence.",
                metadata={"origin": "seed_candidate_only", "trusted_evidence": False},
            )
            for item in current
            if isinstance(item, dict) and item.get("part_number")
        )
        score = score_hits(list(hits))
        decision = VerificationDecision(
            group_keys=tuple(family.get("group_keys") or []),
            oem=None,
            alternatives=alternatives,
            confidence=0.0,
            verified=False,
            sources=hits,
            notes="Seed candidates are not verification evidence; external verification required.",
        ).to_dict()
        decision["auto_approve_threshold"] = threshold
        decision["would_auto_approve_after_external_verification"] = auto_approve(score, threshold)
        decisions.append(decision)

    payload = {
        "contract": "parts_verification_decisions_v1",
        "queue": str(queue_path),
        "threshold": threshold,
        "decisions": decisions,
    }
    save(out_path, payload)
    print(f"Families processed: {len(decisions)}")
    print(f"Output: {out_path}")
    print("No seed data modified. Seed candidate part numbers are treated as untrusted until externally verified.")
    return 0


def wix_audit(
    queue_path: Path,
    vehicles_path: Path,
    out_path: Path,
    cache_path: Path,
    limit: int,
    diagnostic_limit: int,
) -> int:
    queue = load(queue_path)
    families = queue.get("families", []) if isinstance(queue, dict) else []
    vehicles_by_engine = _vehicle_index(vehicles_path)
    results: list[dict[str, Any]] = []

    with VerificationCache(cache_path) as cache:  # type: ignore[attr-defined]
        for family in families[:limit]:
            if not isinstance(family, dict):
                continue
            wix_candidates = [
                item for item in (family.get("current_part_family") or [])
                if isinstance(item, dict) and str(item.get("brand", "")).strip().lower() == "wix"
            ]
            if not wix_candidates:
                continue

            part = normalize_part_number(wix_candidates[0].get("part_number"))
            applications = _wix_applications(part, cache)

            affected_engines = list(family.get("affected_engines") or [])
            engine_matches: dict[str, list[dict[str, Any]]] = {}
            diagnostics: dict[str, list[dict[str, Any]]] = {}
            for engine_code in affected_engines:
                matches: list[dict[str, Any]] = []
                engine_diagnostics: list[dict[str, Any]] = []
                for vehicle in vehicles_by_engine.get(engine_code, []):
                    diagnosis = _diagnose_vehicle(vehicle, applications)
                    if diagnosis["reason"] == "matched":
                        for app in diagnosis.get("matching_applications") or []:
                            matches.append({"vehicle": vehicle, "wix_application": app})
                    elif len(engine_diagnostics) < diagnostic_limit:
                        engine_diagnostics.append(diagnosis)
                if matches:
                    engine_matches[engine_code] = matches
                elif engine_diagnostics:
                    diagnostics[engine_code] = engine_diagnostics
                elif engine_code not in vehicles_by_engine:
                    diagnostics[engine_code] = [{"reason": "engine_code_not_in_vehicle_index"}]

            matched_count = len(engine_matches)
            total = len(affected_engines)
            ratio = (matched_count / total) if total else 0.0
            if total and matched_count == total:
                verdict = "SUPPORTED"
            elif matched_count:
                verdict = "PARTIAL"
            else:
                verdict = "REJECT_CANDIDATE"

            result = {
                "wix_part_number": part,
                "impact": family.get("impact"),
                "group_keys": family.get("group_keys") or [],
                "affected_engines": affected_engines,
                "wix_application_count": len(applications),
                "matched_engine_count": matched_count,
                "match_ratio": round(ratio, 4),
                "verdict": verdict,
                "matched_engines": sorted(engine_matches),
                "diagnostics": diagnostics,
                "applications": applications,
            }
            results.append(result)
            print(
                f"WIX {part}: {verdict}  matched={matched_count}/{total} "
                f"applications={len(applications)}"
            )
            if diagnostic_limit > 0 and verdict != "SUPPORTED":
                shown = 0
                for engine_code, entries in diagnostics.items():
                    if shown >= diagnostic_limit:
                        break
                    first = entries[0] if entries else {"reason": "unknown"}
                    vehicle = first.get("vehicle") or {}
                    expected = " ".join(
                        str(vehicle.get(key) or "")
                        for key in ("make", "model", "engine_label")
                    ).strip()
                    print(f"  {engine_code}: {first.get('reason')}" + (f" | {expected}" if expected else ""))
                    shown += 1

    save(out_path, {
        "contract": "wix_application_audit_v1",
        "queue": str(queue_path),
        "vehicles": str(vehicles_path),
        "results": results,
    })
    print(f"Audit: {out_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoSpec reusable parts verification engine")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Convert a verification queue into review decisions")
    review.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    review.add_argument("--out", type=Path, default=DEFAULT_OUT)
    review.add_argument("--threshold", type=float, default=0.95)

    wix = sub.add_parser("wix-audit", help="Validate queued WIX candidates against official WIX applications")
    wix.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    wix.add_argument("--vehicles", type=Path, default=DEFAULT_VEHICLES)
    wix.add_argument("--out", type=Path, default=DEFAULT_WIX_AUDIT)
    wix.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    wix.add_argument("--limit", type=int, default=20)
    wix.add_argument("--diagnostic-limit", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "review":
        return build_review_decisions(args.queue, args.out, args.threshold)
    if args.command == "wix-audit":
        return wix_audit(args.queue, args.vehicles, args.out, args.cache, args.limit, args.diagnostic_limit)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
