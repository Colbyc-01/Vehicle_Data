import json
from pathlib import Path

from api.engine_resolver import EngineResolver


ROOT = Path(__file__).resolve().parent.parent

resolver = EngineResolver(
    engines=json.loads((ROOT / "data/canonical/engines.json").read_text(encoding="utf-8")),
    label_map=json.loads((ROOT / "data/canonical/engine_alias_map.json").read_text(encoding="utf-8")),
    migration_map=json.loads((ROOT / "data/canonical/engine_code_migration_map.json").read_text(encoding="utf-8")),
    code_aliases=json.loads((ROOT / "data/canonical/engine_code_aliases.json").read_text(encoding="utf-8")),
)


def test_valid_engine_code():
    assert resolver.resolve(engine_code="HONDA_D16") == "HONDA_D16"


def test_invalid_engine_code():
    assert resolver.resolve(engine_code="THIS_DOES_NOT_EXIST") is None


def test_engine_label_resolution():
    assert resolver.resolve(engine_label="1.6L I4") == "HONDA_D16"