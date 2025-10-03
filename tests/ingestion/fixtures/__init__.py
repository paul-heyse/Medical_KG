from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "ingestion"


def load_json_fixture(name: str) -> dict[str, Any]:
    path = _FIXTURE_ROOT / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_text_fixture(name: str) -> str:
    path = _FIXTURE_ROOT / name
    return path.read_text(encoding="utf-8")


def load_bytes_fixture(name: str) -> bytes:
    path = _FIXTURE_ROOT / name
    return path.read_bytes()


__all__ = ["load_json_fixture", "load_text_fixture", "load_bytes_fixture"]
