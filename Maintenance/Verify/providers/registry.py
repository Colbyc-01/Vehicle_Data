from __future__ import annotations

from .base import CatalogProvider
from .catalog import StructuredCatalogProvider
from .fram import FramProvider
from .nhtsa import NhtsaVehicleBackend
from .parts_catalog import PartsCatalogBackend
from .wix import WixProvider


_PROVIDERS: tuple[CatalogProvider, ...] = (
    FramProvider(),
    WixProvider(),
)

_CATALOG = StructuredCatalogProvider((
    NhtsaVehicleBackend(),
    PartsCatalogBackend(),
))


def all_providers() -> tuple[CatalogProvider, ...]:
    return _PROVIDERS


def get_provider(name: str) -> CatalogProvider:
    key = str(name or "").strip().lower()
    for provider in _PROVIDERS:
        if provider.name.lower() == key:
            return provider
    raise KeyError(f"Unknown verification provider: {name}")


def get_catalog_provider() -> StructuredCatalogProvider:
    return _CATALOG
