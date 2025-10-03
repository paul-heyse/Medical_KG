from __future__ import annotations

import pytest

from Medical_KG.ingestion import utils


def test_normalize_text_strips_and_canonicalizes() -> None:
    assert utils.normalize_text(" Café\n") == "Café"


def test_detect_language_handles_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(_value: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(utils, "detect", _fail)
    assert utils.detect_language("text") == "unknown"


def test_generate_doc_id_uses_hash() -> None:
    content = b"example"
    doc_id = utils.generate_doc_id("source", "id", "v1", content)
    assert doc_id.startswith("source:id#v1:")
    assert len(doc_id.split(":")[-1]) == 12
