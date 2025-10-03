from __future__ import annotations

from typing import Iterable, List

import pytest

from Medical_KG.extraction.models import ExtractionBase, ExtractionType, PICOExtraction
from Medical_KG.extraction.service import Chunk, ClinicalExtractionService, extract_pico


def _make_chunk(text: str, *, section: str | None = None) -> Chunk:
    return Chunk(chunk_id="c-1", text=text, doc_id="doc-1", section=section)


def test_service_routes_by_section(clinical_snippets: dict[str, str]) -> None:
    service = ClinicalExtractionService()
    chunk = _make_chunk(clinical_snippets["eligibility"], section="Eligibility")

    results = service.extract(chunk)

    assert results
    assert {extraction.type for extraction in results} == {ExtractionType.ELIGIBILITY}


def test_service_retries_on_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClinicalExtractionService(max_retries=1)
    attempts: list[int] = []

    def flaky_extractor(chunk: Chunk) -> PICOExtraction:
        if not attempts:
            attempts.append(1)
            raise RuntimeError("temporary error")
        extraction = extract_pico(chunk)
        assert extraction is not None
        return extraction

    service._extractors = [(ExtractionType.PICO, flaky_extractor)]

    chunk = _make_chunk("Patients received treatment and placebo.")

    results = service.extract(chunk)

    assert attempts == [1]
    assert results and results[0].type == ExtractionType.PICO


def test_service_dead_letters_invalid_effect() -> None:
    text = "Results reported hazard ratio 0.0 with CI 0.1-0.3"
    chunk = _make_chunk(text, section="Results")
    service = ClinicalExtractionService()

    results = service.extract(chunk)

    assert not results, "Invalid effect should be discarded"
    assert service.dead_letter, "Dead letter queue should capture invalid extraction"


def test_service_builds_envelope_metadata(multi_chunk: Iterable[Chunk]) -> None:
    service = ClinicalExtractionService()

    envelope = service.extract_many(multi_chunk)

    assert envelope.chunk_ids == [chunk.chunk_id for chunk in multi_chunk]
    assert len(envelope.payload) >= 1
    assert len(envelope.schema_hash) == 64
    assert envelope.prompt_hash
    assert envelope.ts.tzinfo is not None


def test_service_raises_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClinicalExtractionService(max_retries=0)

    def exploder(chunk: Chunk) -> List[ExtractionBase]:
        raise RuntimeError("boom")

    service._extractors = [(ExtractionType.PICO, exploder)]

    with pytest.raises(RuntimeError):
        service.extract(_make_chunk("Patients"))

