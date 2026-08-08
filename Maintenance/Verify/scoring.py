from __future__ import annotations

from collections import Counter

from .models import SourceHit
from .normalize import normalize_part_number


def score_hits(hits: list[SourceHit]) -> tuple[float, str]:
    """Return confidence 0..1 and a short reason from independent-source agreement."""
    usable = [
        hit for hit in hits
        if hit.matched_part_number and hit.confidence > 0
    ]
    if not usable:
        return 0.0, "no usable source matches"

    by_part = Counter(normalize_part_number(hit.matched_part_number) for hit in usable)
    part, votes = by_part.most_common(1)[0]
    independent_sources = len({hit.source for hit in usable if normalize_part_number(hit.matched_part_number) == part})

    if independent_sources >= 4:
        return 0.99, f"{independent_sources} independent sources agree"
    if independent_sources == 3:
        return 0.95, "3 independent sources agree"
    if independent_sources == 2:
        return 0.85, "2 independent sources agree"
    return 0.60, "single-source match; review required"


def auto_approve(confidence: float, threshold: float = 0.95) -> bool:
    return confidence >= threshold
