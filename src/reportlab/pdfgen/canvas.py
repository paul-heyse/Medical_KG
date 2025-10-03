from __future__ import annotations

from io import BytesIO
from typing import Sequence


class Canvas:
    """Minimal PDF canvas used for test fixtures."""

    def __init__(self, buffer: BytesIO, pagesize: Sequence[float]) -> None:
        self._buffer = buffer
        self._pagesize = pagesize
        self._lines: list[str] = []
        self._closed = False

    def setFont(self, name: str, size: float) -> None:  # pragma: no cover - formatting only
        self._lines.append(f"FONT {name} {size}")

    def drawString(self, x: float, y: float, text: str) -> None:
        self._lines.append(f"TEXT {x:.2f} {y:.2f} {text}")

    def showPage(self) -> None:
        self._lines.append("PAGE")

    def save(self) -> None:
        if self._closed:
            return
        payload = "\n".join(self._lines).encode("utf-8")
        self._buffer.write(payload)
        self._closed = True


__all__ = ["Canvas"]
