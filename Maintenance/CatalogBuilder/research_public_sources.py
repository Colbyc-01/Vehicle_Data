from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PublicSourceCandidate:
    name: str
    url: str
    useful_for: tuple[str, ...]
    fitment_parts: bool
    license_review_required: bool
    notes: str


PUBLIC_SOURCE_CANDIDATES: tuple[PublicSourceCandidate, ...] = (
    PublicSourceCandidate(
        name="NHTSA vPIC CSV/API",
        url="https://catalog.data.gov/dataset/nhtsa-product-information-catalog-and-vehicle-listing-vpic-vehicle-api-csv",
        useful_for=("vehicle_identity", "vin_decode", "make_model_year"),
        fitment_parts=False,
        license_review_required=False,
        notes="Authoritative public vehicle identity data; not a maintenance-parts catalog.",
    ),
    PublicSourceCandidate(
        name="lifeofcapo/car-api",
        url="https://github.com/lifeofcapo/car-api",
        useful_for=("parts_taxonomy", "vehicle_taxonomy"),
        fitment_parts=False,
        license_review_required=True,
        notes="Contains vehicle and generic parts data, but does not currently appear to provide production-grade vehicle-to-part fitment mapping.",
    ),
    PublicSourceCandidate(
        name="TecDoc catalog wrappers/examples",
        url="https://github.com/ronhartman/tecdoc-autoparts-catalog",
        useful_for=("provider_research", "api_shape"),
        fitment_parts=True,
        license_review_required=True,
        notes="Potential vehicle-to-part/cross-reference capability, but underlying TecDoc data/API rights and access must be verified before ingestion.",
    ),
)


def source_report() -> list[dict[str, object]]:
    return [asdict(item) for item in PUBLIC_SOURCE_CANDIDATES]


if __name__ == "__main__":
    for item in PUBLIC_SOURCE_CANDIDATES:
        print(f"{item.name}: fitment_parts={item.fitment_parts} license_review_required={item.license_review_required}")
        print(f"  {item.url}")
        print(f"  {item.notes}")
