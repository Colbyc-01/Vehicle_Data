from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FitmentSourceResearch:
    name: str
    scope: str
    fitment_parts: bool
    free_tier: bool
    us_focus: bool
    status: str
    notes: str


SOURCES: tuple[FitmentSourceResearch, ...] = (
    FitmentSourceResearch(
        name="TecAlliance TecDoc Web Service",
        scope="global aftermarket vehicle/product/linkage data",
        fitment_parts=True,
        free_tier=False,
        us_focus=False,
        status="commercial",
        notes=(
            "Official TecAlliance service provides structured vehicle, product, OE/cross-reference, "
            "and linkage data. Suitable architecturally, but access is commercial and therefore a future backend."
        ),
    ),
    FitmentSourceResearch(
        name="Fixaroo Parts API",
        scope="UK vehicle parts/fitment API",
        fitment_parts=True,
        free_tier=True,
        us_focus=False,
        status="development_only_candidate",
        notes=(
            "Advertises a free development tier and structured part/fitment endpoints, but is UK/VRM focused. "
            "Useful for exercising the generic catalog adapter, not suitable as AutoSpec's US production source."
        ),
    ),
    FitmentSourceResearch(
        name="NHTSA vPIC",
        scope="US vehicle identity",
        fitment_parts=False,
        free_tier=True,
        us_focus=True,
        status="active",
        notes="Keep as the authoritative public vehicle normalization layer; it does not provide maintenance part numbers.",
    ),
)


def research_manifest() -> list[dict[str, object]]:
    return [asdict(item) for item in SOURCES]


def main() -> int:
    for item in SOURCES:
        print(
            f"{item.name}: status={item.status} fitment_parts={item.fitment_parts} "
            f"free_tier={item.free_tier} us_focus={item.us_focus}"
        )
        print(f"  {item.notes}")
    print()
    print("Recommendation: keep NHTSA active, use any free structured API only to validate the adapter, and avoid treating non-US coverage as production fitment evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
