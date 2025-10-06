from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Protocol

from Medical_KG.ingestion.ledger import LedgerState
from Medical_KG.ir.models import DocumentIR


class LedgerWriter(Protocol):
    def update_state(
        self,
        doc_id: str,
        state: LedgerState,
        *,
        metadata: Mapping[str, str] | None = None,
        adapter: str | None = None,
    ) -> None:
        ...


class IrStorage:
    """Simple content-addressable storage using JSONL files."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    def write(self, document: DocumentIR, *, ledger: LedgerWriter | None = None) -> Path:
        payload = document.as_dict()
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        filename = f"{document.doc_id}-{digest[:12]}.json"
        path = self.base_path / document.source / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() == encoded:
            if ledger is not None:
                ledger.update_state(
                    document.doc_id,
                    LedgerState.IR_READY,
                    metadata={"uri": str(path)},
                    adapter="ir-storage",
                )
            return path
        path.write_bytes(encoded)
        if ledger is not None:
            ledger.update_state(
                document.doc_id,
                LedgerState.IR_READY,
                metadata={"uri": str(path)},
                adapter="ir-storage",
            )
        return path

    def iter_documents(self, source: str) -> Iterable[dict[str, object]]:
        directory = self.base_path / source
        if not directory.exists():
            return []
        documents: list[dict[str, object]] = []
        for file in directory.glob("**/*"):
            if file.is_file():
                data = json.loads(file.read_text())
                documents.append(data)
        return documents
