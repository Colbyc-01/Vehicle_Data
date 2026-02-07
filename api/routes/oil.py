from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/oil-change/by-engine")
def oil_change_by_engine(engine_code: str):
    from api import app_monolith  # type: ignore

    return app_monolith.oil_change_by_engine(engine_code=engine_code)


@router.get("/oil-change/coverage/missing-engine-codes")
def oil_change_coverage_missing_engine_codes():
    from api import app_monolith  # type: ignore

    return app_monolith.oil_change_coverage_missing_engine_codes()
