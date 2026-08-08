from __future__ import annotations

from .base import CatalogProvider
from .wix import WixProvider


_PROVIDERS: tuple[CatalogProvider, ...] = (
    WixProvider(),
)


def all_providers() -> tuple[CatalogProvider, ...]:
    return _PROVIDERS


def get_provider(name: str) -> CatalogProvider:
    key = str(name or "").strip().lower()
    for provider in _PROVIDERS:
        if provider.name.lower() == key:
            return provider
    raise KeyError(f"Unknown verification provider: {name}")
