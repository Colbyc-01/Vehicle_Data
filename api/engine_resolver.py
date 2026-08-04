import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def norm(s):
    if not s:
        return None
    return s.strip().replace("-", "_")


class EngineResolver:
    def __init__(self, engines, label_map, migration_map, code_aliases):
        self.engines = engines
        self.label_map = label_map.get("engine_alias_map", label_map)
        self.migration_map = migration_map
        self.code_aliases = code_aliases

        # valid engine codes
        self.valid = set(engines.keys())

    def resolve(self, engine_code=None, engine_label=None):
        code = norm(engine_code)
        label = norm(engine_label)

        # 1) try code first
        if code:
            code = self.migration_map.get(code, code)
            code = self.code_aliases.get(code, code)

            if code in self.valid:
                return code

        # 2) fallback to label
        if label:
            code = self.label_map.get(label)

            if code:
                code = norm(code)
                code = self.migration_map.get(code, code)
                code = self.code_aliases.get(code, code)

                if code in self.valid:
                    return code

        return None