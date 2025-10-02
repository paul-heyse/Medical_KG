from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, TextIO


class _JsonLinesWriter:
    def __init__(self, handle: TextIO) -> None:
        self._handle = handle

    def write(self, obj: Any) -> None:
        self._handle.write(json.dumps(obj) + "\n")

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "_JsonLinesWriter":  # pragma: no cover - context helper
        return self

    def __exit__(self, *_exc: Any) -> None:  # pragma: no cover - context helper
        self.close()


class _JsonLinesReader:
    def __init__(self, handle: TextIO) -> None:
        self._handle = handle

    def __iter__(self) -> Iterator[Any]:
        for line in self._handle:
            if line.strip():
                yield json.loads(line)

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "_JsonLinesReader":  # pragma: no cover - context helper
        return self

    def __exit__(self, *_exc: Any) -> None:  # pragma: no cover - context helper
        self.close()


def open(path: Path, mode: str = "r") -> _JsonLinesReader | _JsonLinesWriter:
    handle = Path(path).open(mode, encoding="utf-8")
    if "r" in mode:
        return _JsonLinesReader(handle)
    return _JsonLinesWriter(handle)
