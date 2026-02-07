from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter

router = APIRouter()


@router.get("/years")
def years():
    from api import app_monolith  # type: ignore

    return app_monolith.years()


@router.get("/makes")
def makes(year: int):
    from api import app_monolith  # type: ignore

    return app_monolith.makes(year=year)


@router.get("/models")
def models(year: int, make: str):
    from api import app_monolith  # type: ignore

    return app_monolith.models(year=year, make=make)


@router.get("/vehicles/search")
def vehicles_search(
    year: Optional[int] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    q: Optional[str] = None,
):
    """Manual search endpoint used by the Flutter flow."""
    from api import app_monolith  # type: ignore

    return app_monolith.vehicles_search(year=year, make=make, model=model, q=q)
