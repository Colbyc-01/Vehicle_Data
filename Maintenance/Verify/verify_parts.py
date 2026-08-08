from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .models import PartRef, SourceHit, VerificationDecision
from .normalize import normalize_brand, normalize_part_number
from .scoring import auto_approve, score_hits

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE = REPO_ROOT / "air_filter_verification_queue.json"
DEFAULT_OUT = REPO_ROOT / "air_filter_verification_decisions.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def build_review_decisions(queue_path: Path, out_path: Path, threshold: float) -> int:
    queue = load(queue_path)
    families = queue.get("families", []) if isinstance(queue, dict) else []
    decisions: list[dict[str, Any]] = []

    for family in families:
        if not isinstance(family, dict):
            continue
        current = family.get("current_part_family") or []
        hits = [
            SourceHit(
                source=normalize_brand(item.get("brand")) or "unknown",
                query_brand=item.get("brand"),
                query_part_number=item.get("part_number"),
                matched_brand=item.get("brand"),
                matched_part_number=item.get("part_number"),
                confidence=0.60,
                metadata={"origin": "seed_candidate_only"},
            )
            for item in current
            if isinstance(item, dict) and item.get("part_number")
        ]
        confidence, reason = score_hits(hits)
        decision = VerificationDecision(
            group_keys=list(family.get("group_keys") or []),
            oem=None,
            alternatives=[
                PartRef(normalize_brand(item.get("brand")), normalize_part_number(item.get("part_number")))
                for item in current
                if isinstance(item, dict) and item.get("brand") and item.get("part_number")
            ],
            confidence=confidence,
            sources=hits,
            approved=False,
            reason=f"candidate family only; external verification required ({reason})",
        ).to_dict()
        decision["auto_approve_threshold"] = threshold
        decision["would_auto_approve_after_external_verification"] = auto_approve(confidence, threshold)
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
    print("No seed data modified. External source adapters are required before approval.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoSpec reusable parts verification engine")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Convert a verification queue into review decisions")
    review.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    review.add_argument("--out", type=Path, default=DEFAULT_OUT)
    review.add_argument("--threshold", type=float, default=0.95)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "review":
        return build_review_decisions(args.queue, args.out, args.threshold)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
