# Scripts/sanity_check_aliases.py
# Run from project root:
#   python Scripts/sanity_check_aliases.py
#
# What it checks:
# 1) Alias targets exist in Oil_change_specs_seed.json
# 2) Counts how many engine_codes in Engines/engines.json lack specs (after alias resolution)
# 3) Lists top missing codes so you know what actually matters (US-only)

import json
from pathlib import Path
from collections import Counter

# --- Paths (adjust only if your filenames differ) ---
ALIAS_PATH = Path("Maintenance/Contracts/Seeds/engine_alias_map.json")
SPECS_PATH = Path("Maintenance/Contracts/Seeds/Oil_change_specs_seed.json")  # adjust if different
ENGINES_PATH = Path("Engines/engines.json")  # adjust if different

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.as_posix()}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    alias_doc = load_json(ALIAS_PATH)
    alias_map = alias_doc.get("engine_alias_map", {})

    specs_doc = load_json(SPECS_PATH)
    specs_seed = specs_doc.get("oil_change_specs_seed", {})
    specs_keys = set(specs_seed.keys())

    engines_doc = load_json(ENGINES_PATH)
    # engines.json is expected to be: { "ENGINE_CODE": {...meta...}, ... }
    engine_codes = list(engines_doc.keys())

    # --- 1) Alias targets must exist in specs ---
    alias_targets = list(alias_map.values())
    missing_alias_targets = sorted({t for t in alias_targets if t not in specs_keys})

    # --- 2) Coverage check: after resolving each engine_code, do we have specs? ---
    def resolve(code_or_label: str) -> str:
        return alias_map.get(code_or_label, code_or_label)

    missing_after_resolve = []
    for code in engine_codes:
        canonical = resolve(code)
        if canonical not in specs_keys:
            missing_after_resolve.append(code)

    # Frequency of missing (helps find common blockers)
    missing_counts = Counter(missing_after_resolve)

    # --- Output ---
    print("\n=== Sanity Check: Engine Aliases + Oil Specs (US-only) ===\n")

    print(f"Alias map entries: {len(alias_map)}")
    print(f"Specs entries:      {len(specs_keys)}")
    print(f"Engines entries:    {len(engine_codes)}\n")

    print("1) Alias targets missing from specs:")
    if not missing_alias_targets:
        print("   ✅ None. All alias targets exist in Oil_change_specs_seed.\n")
    else:
        print(f"   ❌ {len(missing_alias_targets)} missing alias targets (these are real problems):")
        for t in missing_alias_targets[:50]:
            print(f"    - {t}")
        if len(missing_alias_targets) > 50:
            print(f"    ... (+{len(missing_alias_targets) - 50} more)")
        print()

    print("2) Engines missing specs AFTER alias resolution:")
    missing_total = len(missing_after_resolve)
    coverage = 100.0 * (1 - (missing_total / max(1, len(engine_codes))))
    print(f"   Missing: {missing_total} / {len(engine_codes)}")
    print(f"   Coverage: {coverage:.1f}%\n")

    print("Top 30 missing engine_codes (raw inputs) by frequency:")
    # Most should be 1, but this still helps spot patterns.
    for code, ct in missing_counts.most_common(30):
        print(f"  - {code}  (x{ct})")

    print("\nInterpretation:")
    print(" - If section (1) has any missing alias targets, fix those first (bad aliases).")
    print(" - Section (2) mostly reflects unsupported/non-US/low-volume codes — which is OK for US-only Tier-1.")
    print(" - You should NOT try to drive missing to zero; just ensure common US engines resolve + have specs.\n")

if __name__ == "__main__":
    main()
