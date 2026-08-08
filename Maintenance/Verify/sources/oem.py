from __future__ import annotations

from ..models import SourceHit
from .base import PartSource


class OEMSource(PartSource):
    """Base OEM lookup adapter."""

    name = "OEM"

    def lookup(
        self,
        brand: str,
        part_number: str,
    ) -> list[SourceHit]:
        """
        Lookup an OEM part number.

        Subclasses implement the actual lookup.
        """
        raise NotImplementedError(
            f"{brand} OEM lookup not implemented."
        )