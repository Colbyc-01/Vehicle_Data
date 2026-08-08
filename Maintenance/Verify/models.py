from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PartRef:
    brand: str
    part_number: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceHit:
    source: str
    query_brand: str | None
    query_part_number: str | None
    matched_brand: str | None
    matched_part_number: str | None
    url: str | None = None
    description: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationDecision:
    group_keys: list[str]
    oem: PartRef | None
    alternatives: list[PartRef]
    confidence: float
    sources: list[SourceHit]
    approved: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_keys": self.group_keys,
            "oem": self.oem.to_dict() if self.oem else None,
            "alternatives": [item.to_dict() for item in self.alternatives],
            "confidence": round(self.confidence, 4),
            "approved": self.approved,
            "reason": self.reason,
            "sources": [hit.to_dict() for hit in self.sources],
        }
