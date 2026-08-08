from __future__ import annotations
import re

_BRAND_ALIASES = {
    "fram": "FRAM", "wix": "WIX", "purolator": "Purolator",
    "mann": "MANN", "mann-filter": "MANN", "mahle": "Mahle",
    "k&n": "K&N", "kn": "K&N", "acdelco": "ACDelco",
    "ac delco": "ACDelco", "motorcraft": "Motorcraft",
    "mopar": "Mopar", "honda": "Honda", "acura": "Acura",
    "toyota": "Toyota", "lexus": "Lexus", "audi": "Audi",
    "volkswagen": "Volkswagen", "vw": "Volkswagen", "bmw": "BMW",
}

def clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""

def normalize_brand(value: object) -> str:
    raw = clean(value)
    return _BRAND_ALIASES.get(raw.lower(), raw)

def normalize_part_number(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())

def same_part_number(a: object, b: object) -> bool:
    na = normalize_part_number(a)
    nb = normalize_part_number(b)
    return bool(na and nb and na == nb)
