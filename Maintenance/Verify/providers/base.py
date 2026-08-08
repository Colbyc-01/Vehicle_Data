from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import PartRef, SourceHit


class CatalogProvider(ABC):
    name: str

    @abstractmethod
    def lookup_part(self, part_number: str) -> list[SourceHit]:
        raise NotImplementedError

    def lookup_oem(self, oem_number: str) -> list[SourceHit]:
        return self.lookup_part(oem_number)

    @staticmethod
    def query_part(brand: str, part_number: str) -> PartRef:
        return PartRef(brand=brand, part_number=part_number)
