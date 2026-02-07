from __future__ import annotations
from typing import Any, Dict, Optional

from .utils import seed_to_raw

def find_by_engine(items, engine_code: str) -> Optional[Dict[str, Any]]:
    raw = seed_to_raw(engine_code)
    for it in items or []:
        if seed_to_raw(it.get("engine_code")) == raw:
            return it
    return None

def find_by_vehicle_key(items, vehicle_key: str):
    vk = (vehicle_key or "").strip().lower()
    if not vk:
        return None
    for it in items or []:
        sk = (it.get("vehicle_key") or "").strip().lower()
        if not sk:
            continue
        if sk == vk:
            return it
        if sk.startswith(vk + "_"):
            return it
        if vk.startswith(sk + "_"):
            return it
    return None

def vehicle_key_from(v: Dict[str, Any]) -> str:
    make = (v.get("make") or "").strip().lower()
    model = (v.get("model") or "").strip().lower()
    return f"{make}_{model}".replace(" ", "_")
