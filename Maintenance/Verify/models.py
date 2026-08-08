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
    query: PartRef
    matched_part: PartRef | None
    url: str | None = None
    confidence: float = 0.0
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class VerificationDecision:
    group_keys: tuple[str, ...]
    oem: PartRef | None
    alternatives: tuple[PartRef, ...]
    confidence: float
    verified: bool
    sources: tuple[SourceHit, ...]
    notes: str = ""
    def to_dict(self) -> dict[str, Any]:
        return {
            "group_keys": list(self.group_keys),
            "oem": (
                {"brand": self.oem.brand, "part_number": self.oem.part_number, "verified": self.verified}
                if self.oem else None
            ),
            "alternatives": [part.to_dict() for part in self.alternatives],
            "confidence": round(self.confidence, 4),
            "verified": self.verified,
            "sources": [hit.to_dict() for hit in self.sources],
            "notes": self.notes,
        }
