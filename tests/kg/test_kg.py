from __future__ import annotations

import pytest

from Medical_KG.kg.fhir import ConceptLexicon, EvidenceExporter
from Medical_KG.kg.schema import CDKOSchema
from Medical_KG.kg.validators import DeadLetterQueue, KgValidationError, KgValidator
from Medical_KG.kg.writer import KnowledgeGraphWriter


def test_schema_default_contains_expected_nodes() -> None:
    schema = CDKOSchema.default()
    description = schema.describe()
    assert "Document" in description["nodes"]
    assert "HAS_CHUNK" in description["relationships"]
    assert any("doc_uri_unique" in constraint for constraint in description["constraints"])


def test_knowledge_graph_writer_generates_statements() -> None:
    writer = KnowledgeGraphWriter()
    writer.write_document({"id": "doc-1", "uri": "doc://1", "source": "pmc"})
    writer.write_chunk({"id": "chunk-1", "text": "hello"}, document_uri="doc://1", order=0)
    writer.write_outcome({"id": "out-1", "loinc": "1234-5"})
    writer.write_evidence_variable({"id": "ev-1", "provenance": ["activity"]}, document_uri="doc://1")
    writer.write_evidence({"id": "e-1", "provenance": ["activity"], "unit_ucum": "mg"}, outcome_id="out-1", variable_id="ev-1")
    statements = list(writer.statements)
    assert any("MERGE (n:Document" in stmt.cypher for stmt in statements)
    assert any("HAS_CHUNK" in stmt.cypher for stmt in statements)


def test_validator_records_dead_letters() -> None:
    dead_letter = DeadLetterQueue()
    validator = KgValidator(ucum_codes={"mg"}, dead_letter=dead_letter)
    nodes = [
        {"label": "Outcome", "id": "out-1", "loinc": "1234-5", "unit_ucum": "mg"},
        {"label": "Evidence", "id": "ev-1", "unit_ucum": "invalid", "provenance": ["run"], "outcome_loinc": "1234-5"},
    ]
    relationships = [{"type": "MEASURES", "start_id": "ev-1", "end_id": "out-1"}]
    with pytest.raises(KgValidationError):
        validator.validate_batch(nodes, relationships)
    assert any("UCUM" in issue.reason for issue in dead_letter.entries)


def test_validator_requires_provenance() -> None:
    validator = KgValidator(ucum_codes={"mg"})
    nodes = [
        {"label": "Outcome", "id": "out-1", "loinc": "1234-5", "unit_ucum": "mg"},
        {"label": "Evidence", "id": "ev-1", "unit_ucum": "mg", "outcome_loinc": "1234-5"},
    ]
    relationships = [{"type": "MEASURES", "start_id": "ev-1", "end_id": "out-1"}]
    with pytest.raises(KgValidationError):
        validator.validate_batch(nodes, relationships)


def test_fhir_exporter_validates_codes() -> None:
    lexicon = ConceptLexicon({"http://snomed.info/sct": {"123"}})
    exporter = EvidenceExporter(lexicon=lexicon, ucum_codes={"mg"})
    node = {
        "id": "evvar-1",
        "name": "Population",
        "characteristic": [
            {"concept": {"system": "http://snomed.info/sct", "code": "123"}},
        ],
    }
    resource = exporter.export_evidence_variable(node)
    assert resource.payload["resourceType"] == "EvidenceVariable"

    with pytest.raises(ValueError):
        exporter.export_evidence_variable(
            {
                "id": "evvar-2",
                "name": "Population",
                "characteristic": [
                    {"concept": {"system": "http://snomed.info/sct", "code": "999"}},
                ],
            }
        )
