from __future__ import annotations

import re


_BRAND_ALIASES = {
    "ac delco": "ACDelco",
    "acdelco": "ACDelco",
    "fram": "FRAM",
    "wix": "WIX",
    "purolator": "Purolator",
    "mann": "MANN",
    "mann-filter": "MANN",
    "mahle": "Mahle",
    "k&n": "K&N",
    "kn": "K&N",
}


def normalize_brand(value: str | None) -> str:
    raw = (value or "").strip()
    return _BRAND_ALIASES.get(raw.lower(), raw)


def normalize_part_number(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").strip().upper())


def same_part(a_brand: str | None, a_number: str | None, b_brand: str | None, b_number: str | None) -> bool:
    return (
        normalize_brand(a_brand).lower() == normalize_brand(b_brand).lower()
        and normalize_part_number(a_number) == normalize_part_number(b_number)
    )
