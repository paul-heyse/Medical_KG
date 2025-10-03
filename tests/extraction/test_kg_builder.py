from __future__ import annotations

from Medical_KG.extraction.kg import build_kg_statements


def test_build_kg_statements_generates_activity(extraction_envelope) -> None:
    statements = list(build_kg_statements(extraction_envelope, document_uri="doc://123", study_id="NCT0000"))

    assert statements
    cypher_statements = {statement.cypher for statement in statements}
    assert any("ExtractionActivity" in cypher for cypher in cypher_statements)
    assert any("EvidenceVariable" in cypher for cypher in cypher_statements)
    assert any("AdverseEvent" in cypher for cypher in cypher_statements)
    assert any("Intervention" in cypher for cypher in cypher_statements)
    assert any("EligibilityConstraint" in cypher for cypher in cypher_statements)


def test_build_kg_statements_links_generated_by(extraction_envelope) -> None:
    statements = list(build_kg_statements(extraction_envelope, document_uri="doc://123"))

    generated = [s for s in statements if "WAS_GENERATED_BY" in s.cypher]
    assert generated, "KG builder should link extractions to the activity node"

