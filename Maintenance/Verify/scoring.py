from __future__ import annotations
from collections import Counter
from .models import SourceHit
from .normalize import normalize_part_number

def score_hits(hits: list[SourceHit]) -> float:
    confirmed = [h for h in hits if h.matched_part and normalize_part_number(h.matched_part.part_number)]
    if not confirmed:
        return 0.0
    counts = Counter(normalize_part_number(h.matched_part.part_number) for h in confirmed if h.matched_part)
    top_count = counts.most_common(1)[0][1]
    source_count = len({h.source.lower() for h in confirmed})
    agreement = top_count / len(confirmed)
    return max(0.0, min(1.0, agreement * 0.70 + min(source_count, 4) / 4 * 0.30))

def auto_verify(score: float, minimum: float = 0.95) -> bool:
    return score >= minimum

def auto_approve(score: float, minimum: float = 0.95) -> bool:
    return auto_verify(score, minimum)
