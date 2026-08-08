from __future__ import annotations
from abc import ABC, abstractmethod
try:
    from ..models import PartRef, SourceHit
except ImportError:
    from models import PartRef, SourceHit

class PartSource(ABC):
    name: str

    @abstractmethod
    def lookup(self, part: PartRef) -> list[SourceHit]:
        raise NotImplementedError
