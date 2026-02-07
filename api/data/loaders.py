from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

import json

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_optional(path: Path) -> Dict[str, Any]:
    try:
        return load_json(path)
    except Exception:
        return {"items": []}
