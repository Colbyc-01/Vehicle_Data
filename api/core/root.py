from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return repo root anchored off this file location (never CWD-dependent)."""
    return Path(__file__).resolve().parents[2]
