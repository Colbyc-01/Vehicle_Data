from __future__ import annotations
import json
from typing import Any, Dict

from purchase_links import build_buy_links

from api.data.loaders import load_json
from api.data.paths import ENGINE_AIR_FILTER_GROUPS_PATH, CABIN_AIR_FILTER_GROUPS_PATH

def _deepcopy(obj: Any) -> Any:
    return json.loads(json.dumps(obj))

def hydrate_engine_air_filter(item: dict) -> dict:
    """Normalize engine air filter payload to the Flutter UI contract.
    Mirrors your prior working behavior in app.py.
    """
    if not isinstance(item, dict):
        return {"items": [], "warning": "not covered"}

    def _attach_buy_links(af: dict) -> dict:
        if not isinstance(af, dict):
            return af
        out_af = _deepcopy(af)
        oem = out_af.get("oem")
        if isinstance(oem, dict):
            oem["buy_links"] = build_buy_links(oem)
        alts = out_af.get("alternatives")
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    alt["buy_links"] = build_buy_links(alt)
        return out_af

    # 1) Inline air_filter present
    af = item.get("air_filter")
    if isinstance(af, dict):
        out = dict(item)
        out["air_filter"] = _attach_buy_links(af)
        return out

    # 2) Group indirection (preferred normalized storage)
    group_key = item.get("engine_air_filter_group") or item.get("group_key")
    if isinstance(group_key, str) and group_key.strip():
        try:
            groups_doc = load_json(ENGINE_AIR_FILTER_GROUPS_PATH)
            grp = groups_doc.get(group_key.strip())
            if isinstance(grp, dict):
                out = dict(item)
                out["air_filter"] = _attach_buy_links(grp)
                return out
        except Exception:
            pass

    # 3) Legacy list schema fallback (kept for tolerance)
    legacy = item.get("engine_air_filter")
    if isinstance(legacy, list) and legacy:
        row0 = legacy[0] if isinstance(legacy[0], dict) else None
        if isinstance(row0, dict):
            oem_brand = row0.get("oem_brand")
            oem_part = row0.get("oem_part_number")
            if oem_part and str(oem_part).strip().upper() != "TBD":
                out = dict(item)
                out["air_filter"] = _attach_buy_links(
                    {
                        "oem": {"brand": oem_brand, "part_number": oem_part},
                        "alternatives": [],
                    }
                )
                return out

    return item

def hydrate_cabin_air_filter(item: dict) -> dict:
    """Normalize cabin air filter payload to the Flutter UI contract.
    Mirrors your prior working behavior in app.py.
    """
    if not isinstance(item, dict):
        return {"items": [], "warning": "not covered"}

    def _attach_buy_links(cf: dict) -> dict:
        if not isinstance(cf, dict):
            return cf
        out_cf = _deepcopy(cf)
        primary = out_cf.get("primary") or out_cf.get("oem")
        if isinstance(primary, dict):
            primary["buy_links"] = build_buy_links(primary)
            out_cf["primary"] = primary
        alts = out_cf.get("alternatives")
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    alt["buy_links"] = build_buy_links(alt)
        spec = out_cf.get("spec")
        if not isinstance(spec, dict):
            spec = {}
        if not spec.get("filter_type"):
            spec["filter_type"] = "cabin"
        out_cf["spec"] = spec
        return out_cf

    cf = item.get("cabin_filter")
    if isinstance(cf, dict):
        out = dict(item)
        out["cabin_filter"] = _attach_buy_links(cf)
        return out

    group_key = item.get("cabin_filter_group_key") or item.get("group_key")
    if isinstance(group_key, str) and group_key.strip():
        try:
            groups_doc = load_json(CABIN_AIR_FILTER_GROUPS_PATH)
            groups = groups_doc.get("groups") if isinstance(groups_doc, dict) else None
            if not isinstance(groups, dict):
                groups = groups_doc
            grp = groups.get(group_key.strip()) if isinstance(groups, dict) else None
            if isinstance(grp, dict):
                out = dict(item)
                out["cabin_filter"] = _attach_buy_links(grp)
                return out
        except Exception:
            pass

    return item
