#!/usr/bin/env python3
"""
Engine dataset validator (vehicles + seeds + resolver maps)

Usage:
  python validate_engine_data.py \
    --vehicles vehicles.json \
    --engines engines.json \
    --oil oil_specs_seed.json \
    --disamb engine_disambiguation_map.cleaned.json \
    --migration engine_code_migration_map.final.json \
    --code-aliases engine_code_aliases.json \
    --out engine_data_validator_report.json

Exit codes:
  0 = OK (no missing after resolution, no blocked consumer-unsafe codes)
  2 = Missing engine codes after resolution (hard fail)
  3 = Consumer-unsafe / needs_oem / needs_disambiguation codes referenced (fail if you want strict consumer safety)
"""
import argparse, json, os

def load(p):
    with open(p,"r",encoding="utf-8") as f:
        return json.load(f)

def extract_oil_codes(oil):
    oil_codes=[]
    if isinstance(oil, dict):
        if "items" in oil and isinstance(oil["items"], list):
            for it in oil["items"]:
                if isinstance(it, dict) and it.get("engine_code"):
                    oil_codes.append(it["engine_code"])
        else:
            for k,v in oil.items():
                if isinstance(v, dict):
                    oil_codes.append(k)
    elif isinstance(oil, list):
        for it in oil:
            if isinstance(it, dict) and it.get("engine_code"):
                oil_codes.append(it["engine_code"])
    return oil_codes

def resolve_engine_code(code, migration, code_aliases, disamb_map, vin_attrs=None):
    c = (code or "").strip()
    c = migration.get(c, c)
    c = code_aliases.get(c, c)

    entry = disamb_map.get(c)
    if entry:
        if isinstance(entry, str):
            c = entry
        elif isinstance(entry, dict) and vin_attrs:
            for r in (entry.get("rules") or []):
                when = r.get("when") or {}
                ok=True
                for k,v in when.items():
                    if vin_attrs.get(k) != v:
                        ok=False
                        break
                if ok and r.get("engine_code"):
                    c = r["engine_code"]
                    break
    return c

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vehicles", required=True)
    ap.add_argument("--engines", required=True)
    ap.add_argument("--oil", required=False)
    ap.add_argument("--disamb", required=True)
    ap.add_argument("--migration", required=True)
    ap.add_argument("--code-aliases", required=True)
    ap.add_argument("--out", default="engine_data_validator_report.json")
    args=ap.parse_args()

    vehicles=load(args.vehicles)
    engines=load(args.engines)
    disamb=load(args.disamb)
    migration=load(args.migration)
    code_aliases=load(args.code_aliases)

    engine_keys=set(engines.keys())

    vehicle_codes=[]
    for v in vehicles.get("vehicles", []):
        for c in (v.get("engine_codes") or []):
            vehicle_codes.append(c)

    oil_codes=[]
    if args.oil and os.path.exists(args.oil):
        oil=load(args.oil)
        oil_codes=extract_oil_codes(oil)

    def check(codes):
        missing=[]
        blocked=[]
        for c in codes:
            r=resolve_engine_code(c, migration, code_aliases, disamb_map=disamb, vin_attrs=None)
            if r not in engine_keys:
                missing.append({"raw":c,"resolved":r})
            else:
                rec=engines.get(r,{})
                ver=rec.get("verification") if isinstance(rec.get("verification"), dict) else {}
                lvl=ver.get("level")
                if lvl in ("needs_oem","needs_disambiguation") or ver.get("consumer_safe") is False:
                    blocked.append({"raw":c,"resolved":r,"verification":ver})
        return missing, blocked

    v_miss, v_block = check(vehicle_codes)
    o_miss, o_block = check(oil_codes)

    report={
        "counts":{
            "vehicles_unique": len(set(vehicle_codes)),
            "oil_unique": len(set(oil_codes)),
            "engines_total": len(engine_keys),
            "vehicles_missing_after_resolve": len({d["resolved"] for d in v_miss}),
            "oil_missing_after_resolve": len({d["resolved"] for d in o_miss}),
            "vehicles_blocked": len(v_block),
            "oil_blocked": len(o_block),
        },
        "missing_after_resolve":{
            "vehicles": v_miss[:200],
            "oil": o_miss[:200],
        },
        "blocked_consumer_unsafe":{
            "vehicles": v_block[:200],
            "oil": o_block[:200],
        }
    }

    with open(args.out,"w",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)

    if report["counts"]["vehicles_missing_after_resolve"] or report["counts"]["oil_missing_after_resolve"]:
        print("FAIL: missing engine codes after resolution.")
        return 2
    if report["counts"]["vehicles_blocked"] or report["counts"]["oil_blocked"]:
        print("FAIL: consumer-unsafe (needs_oem/disambiguation) engine codes referenced.")
        return 3

    print("OK: all codes resolve and are consumer-safe.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
