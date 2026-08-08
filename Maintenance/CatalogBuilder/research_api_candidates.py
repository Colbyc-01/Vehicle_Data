from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiCandidate:
    name: str
    status: str
    free_tier: bool
    us_focus: bool
    fitment_parts: bool
    production_candidate: bool
    notes: str


CANDIDATES = (
    ApiCandidate(
        name="AutoPartsAPI",
        status="trial_candidate",
        free_tier=True,
        us_focus=True,
        fitment_parts=True,
        production_candidate=True,
        notes=(
            "Structured endpoints for manufacturers, models, vehicles, articles, OEM numbers, VIN, and related catalog data. "
            "Free trial/no-card access is advertised; paid plans start low enough to consider later if the trial proves US coverage and accuracy."
        ),
    ),
    ApiCandidate(
        name="VehDB",
        status="vehicle_data_only",
        free_tier=True,
        us_focus=True,
        fitment_parts=False,
        production_candidate=False,
        notes=(
            "Useful vehicle/spec/recall/tire-fitment API with a free tier, but not a general maintenance-parts catalog. "
            "Keep NHTSA as the current free vehicle resolver unless VehDB adds value later."
        ),
    ),
    ApiCandidate(
        name="MOTOR Parts Data",
        status="commercial_future",
        free_tier=False,
        us_focus=True,
        fitment_parts=True,
        production_candidate=True,
        notes=(
            "Strong US OE/aftermarket parts and YMME fitment data, ACES/PIES aligned, available by API or bulk export. "
            "Commercial source for a later revenue-backed upgrade."
        ),
    ),
)


def main() -> int:
    for item in CANDIDATES:
        print(
            f"{item.name}: status={item.status} free_tier={item.free_tier} "
            f"us_focus={item.us_focus} fitment_parts={item.fitment_parts} "
            f"production_candidate={item.production_candidate}"
        )
        print(item.notes)
        print()

    print("Recommendation: test AutoPartsAPI first. It is the strongest current low-cost structured US parts-fitment lead; keep all returned data discovery-only until provider/application verification passes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
