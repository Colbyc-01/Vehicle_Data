from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, Body

router = APIRouter()

@router.post("/vin/resolve")
def vin_resolve(payload: Dict[str, Any] = Body(...)):
    from api import app_monolith  # type: ignore
    return app_monolith.vin_resolve(payload)

@router.post("/vin/resolve_and_bundle")
def vin_resolve_and_bundle(payload: Dict[str, Any] = Body(...)):
    from api import app_monolith  # type: ignore
    return app_monolith.vin_resolve_and_bundle(payload)
