from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS lookup_cache (
    source TEXT NOT NULL,
    query_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source, query_key)
)
"""


class VerificationCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def get(self, source: str, query_key: str) -> Any | None:
        row = self.conn.execute(
            "SELECT payload FROM lookup_cache WHERE source=? AND query_key=?",
            (source, query_key),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, source: str, query_key: str, payload: Any) -> None:
        self.conn.execute(
            "INSERT INTO lookup_cache(source, query_key, payload) VALUES(?,?,?) "
            "ON CONFLICT(source, query_key) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP",
            (source, query_key, json.dumps(payload, sort_keys=True)),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
