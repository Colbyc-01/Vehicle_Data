from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationCategory:
    key: str
    label: str
    candidate_brands: tuple[str, ...] = ()


CATEGORIES: dict[str, VerificationCategory] = {
    "engine_air_filter": VerificationCategory(
        key="engine_air_filter",
        label="Engine Air Filter",
        candidate_brands=("WIX", "FRAM", "PUROLATOR", "MANN", "MAHLE"),
    ),
    "cabin_air_filter": VerificationCategory(
        key="cabin_air_filter",
        label="Cabin Air Filter",
        candidate_brands=("WIX", "FRAM", "PUROLATOR", "MANN", "MAHLE"),
    ),
    "oil_filter": VerificationCategory(
        key="oil_filter",
        label="Oil Filter",
        candidate_brands=("WIX", "FRAM", "PUROLATOR", "MANN", "MAHLE"),
    ),
    "spark_plug": VerificationCategory(
        key="spark_plug",
        label="Spark Plug",
    ),
    "serpentine_belt": VerificationCategory(
        key="serpentine_belt",
        label="Serpentine Belt",
    ),
    "timing_belt": VerificationCategory(
        key="timing_belt",
        label="Timing Belt",
    ),
    "brake_pad": VerificationCategory(
        key="brake_pad",
        label="Brake Pad",
    ),
    "wheel_bearing": VerificationCategory(
        key="wheel_bearing",
        label="Wheel Bearing",
    ),
}


def get_category(name: str) -> VerificationCategory:
    key = str(name or "").strip().lower()
    try:
        return CATEGORIES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown verification category: {name}") from exc
