from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..models import PartRef, SourceHit


@dataclass(frozen=True)
class CatalogApplication:
    make: str
    model: str
    year_min: int | None
    year_max: int | None
    engine: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class CatalogVehicleQuery:
    make: str
    model: str
    year_min: int | None = None
    year_max: int | None = None
    engine: str = ""


class CatalogProvider(ABC):
    name: str

    @abstractmethod
    def lookup_part(self, part_number: str) -> list[SourceHit]:
        raise NotImplementedError

    def lookup_oem(self, oem_number: str) -> list[SourceHit]:
        return self.lookup_part(oem_number)

    def lookup_interchange(self, brand: str, part_number: str) -> list[SourceHit]:
        """Cross-reference another manufacturer's part into this catalog."""
        return []

    def lookup_vehicle(self, query: CatalogVehicleQuery) -> list[SourceHit]:
        """Discover catalog parts by vehicle fitment when a provider supports it."""
        return []

    @property
    def supports_vehicle_lookup(self) -> bool:
        return self.__class__.lookup_vehicle is not CatalogProvider.lookup_vehicle

    @property
    def supports_interchange_lookup(self) -> bool:
        return self.__class__.lookup_interchange is not CatalogProvider.lookup_interchange

    def applications_for_part(self, part_number: str) -> list[CatalogApplication]:
        applications: list[CatalogApplication] = []
        for hit in self.lookup_part(part_number):
            raw = hit.metadata.get("applications") if isinstance(hit.metadata, dict) else None
            if not isinstance(raw, list):
                continue
            for item in raw:
                if not isinstance(item, dict):
                    continue
                applications.append(
                    CatalogApplication(
                        make=str(item.get("make") or ""),
                        model=str(item.get("model") or ""),
                        year_min=item.get("year_min") if isinstance(item.get("year_min"), int) else None,
                        year_max=item.get("year_max") if isinstance(item.get("year_max"), int) else None,
                        engine=str(item.get("engine") or ""),
                        metadata={k: v for k, v in item.items() if k not in {"make", "model", "year_min", "year_max", "engine"}},
                    )
                )
        return applications

    @staticmethod
    def query_part(brand: str, part_number: str) -> PartRef:
        return PartRef(brand=brand, part_number=part_number)
