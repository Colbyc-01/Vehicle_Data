import json
from pathlib import Path

class EngineResolver:
    def __init__(self, alias_map_path: Path):
        with open(alias_map_path, "r") as f:
            doc = json.load(f)

        self.market_scope = doc.get("market_scope", "US_only")
        self.alias_map = doc.get("engine_alias_map", {})

    def resolve(self, engine_code_or_label: str) -> str:
        """
        Resolve an engine code or label to its canonical engine_code.
        One-hop only. US-market only.
        """
        if not engine_code_or_label:
            return engine_code_or_label

        return self.alias_map.get(engine_code_or_label, engine_code_or_label)
