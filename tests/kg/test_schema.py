import pytest

from Medical_KG.kg.schema import CDKOSchema
from Medical_KG.kg.validators import KgValidationError, KgValidator
from Medical_KG.kg.writer import KnowledgeGraphWriter


def test_schema_contains_expected_constraints() -> None:
    schema = CDKOSchema.default()
    statements = schema.as_statements()
    assert any("doc_uri_unique" in stmt for stmt in statements["constraints"])
    assert any("chunk_qwen_idx" in stmt for stmt in statements["indexes"])


def test_writer_generates_cypher() -> None:
    writer = KnowledgeGraphWriter()
    writer.write_document({
        "id": "doc-1",
        "source": "clinicaltrials",
        "uri": "https://example.com",
        "title": "Sample",
        "language": "en",
        "publication_date": "2024-01-01",
        "meta": {},
    })
    writer.write_chunk({
        "id": "chunk-1",
        "text": "Example",
        "section": "introduction",
        "start": 0,
        "end": 7,
        "token_count": 2,
        "intent": "evidence",
        "path": "doc-1#0",
    })
    writer.write_relationship("HAS_CHUNK", "doc-1", "chunk-1", {"index": 0})
    statements = list(writer.statements)
    assert statements[0].parameters["id"] == "doc-1"
    assert "MERGE" in statements[-1].cypher


def test_validator_checks_ucum_and_provenance() -> None:
    validator = KgValidator(ucum_codes={"mg"})
    with pytest.raises(KgValidationError):
        validator.validate_node({"label": "Evidence", "unit_ucum": "g", "provenance": []})
    with pytest.raises(KgValidationError):
        validator.validate_relationship({"type": "HAS_AE", "count": -1})
