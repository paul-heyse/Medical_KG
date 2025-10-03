from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from Medical_KG.ir.models import DocumentIR


class IrStorage:
    """Simple content-addressable storage using JSONL files."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    def write(self, document: DocumentIR, *, ledger: Any | None = None) -> Path:
        payload = document.as_dict()
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        filename = f"{document.doc_id}-{digest[:12]}.json"
        path = self.base_path / document.source / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() == encoded:
            if ledger is not None:
                ledger.record(document.doc_id, "ir_exists", {"uri": str(path)})
            return path
        path.write_bytes(encoded)
        if ledger is not None:
            ledger.record(document.doc_id, "ir_written", {"uri": str(path)})
        return path

    def iter_documents(self, source: str) -> Iterable[dict[str, Any]]:
        directory = self.base_path / source
        if not directory.exists():
            return []
        documents: list[dict[str, Any]] = []
        for file in directory.glob("**/*"):
            if file.is_file():
                data = json.loads(file.read_text())
                documents.append(data)
        return documents
