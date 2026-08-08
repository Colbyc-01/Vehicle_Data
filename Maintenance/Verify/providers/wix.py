from __future__ import annotations

from ..models import PartRef, SourceHit
from ..sources.wix import WIX_APPLICATION_URL, fetch_applications
from .base import CatalogProvider


class WixProvider(CatalogProvider):
    name = "WIX"

    def lookup_part(self, part_number: str) -> list[SourceHit]:
        query = PartRef(brand=self.name, part_number=str(part_number or "").strip())
        if not query.part_number:
            return []

        applications = fetch_applications(query.part_number)
        url = WIX_APPLICATION_URL.format(part=query.part_number)
        if not applications:
            return [
                SourceHit(
                    source=self.name,
                    query=query,
                    matched_part=None,
                    url=url,
                    confidence=0.0,
                    notes="No WIX applications returned for this part number.",
                )
            ]

        return [
            SourceHit(
                source=self.name,
                query=query,
                matched_part=query,
                url=url,
                confidence=1.0,
                notes=f"WIX catalog returned {len(applications)} applications.",
                metadata={"applications": [application.to_dict() for application in applications]},
            )
        ]
