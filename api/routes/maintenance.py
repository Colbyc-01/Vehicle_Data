from __future__ import annotations
from typing import Optional

from fastapi import APIRouter

from api.services.maintenance_service import build_maintenance_bundle

router = APIRouter()

@router.get("/maintenance/bundle")
def maintenance_bundle(vehicle_id: str, year: int, engine_code: Optional[str] = None):
    # Import from monolith at runtime so you can keep your existing oil logic untouched for now.
    from api import app_monolith  # type: ignore
    return build_maintenance_bundle(
        reload_all=app_monolith.reload_all,
        oil_change_by_engine=app_monolith.oil_change_by_engine,
        vehicle_id=vehicle_id,
        year=year,
        engine_code=engine_code,
    )
