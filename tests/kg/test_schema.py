from Medical_KG.kg.schema import CDKOSchema, NodeProperty, NodeSchema


def test_node_schema_partitions_required_and_optional() -> None:
    schema = NodeSchema(
        label="Example",
        properties=[
            NodeProperty("id", "string", required=True, description="identifier"),
            NodeProperty("label", "string", description="display"),
        ],
    )
    details = schema.as_dict()
    assert details["required"] == [{"name": "id", "type": "string", "description": "identifier"}]
    assert details["optional"] == [{"name": "label", "type": "string", "description": "display"}]


def test_default_schema_contains_expected_relationships() -> None:
    schema = CDKOSchema.default()
    assert "Document" in schema.nodes
    assert "HAS_CHUNK" in schema.relationships
    constraint_statements = [constraint.statement for constraint in schema.constraints]
    assert any("Document" in stmt for stmt in constraint_statements)
