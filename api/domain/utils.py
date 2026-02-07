from __future__ import annotations
import re
from typing import Any, Optional

def norm(s: Any) -> str:
    if s is None:
        return ""
    return " ".join(str(s).strip().split()).casefold()

def seed_to_raw(code: str) -> Optional[str]:
    if not code:
        return None
    if "_" in code:
        return code.split("_", 1)[1]
    return code

def as_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None

def key_alnum(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm(s))
