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


def test_schema_constraints_include_identifier_uniqueness() -> None:
    schema = CDKOSchema.default()
    statements = [constraint.statement for constraint in schema.constraints]
    assert any("Identifier" in stmt and "IS UNIQUE" in stmt for stmt in statements)


def test_schema_indexes_cover_vector_and_fulltext() -> None:
    schema = CDKOSchema.default()
    statements = [index.statement for index in schema.indexes]
    assert any("VECTOR INDEX chunk_qwen_idx" in stmt for stmt in statements)
    assert any("FULLTEXT INDEX chunk_text_ft" in stmt for stmt in statements)


def test_schema_migration_diff_detects_removed_constraint() -> None:
    baseline = CDKOSchema.default()
    modified = CDKOSchema.default()
    removed = modified.constraints.pop()
    baseline_statements = {constraint.statement for constraint in baseline.constraints}
    modified_statements = {constraint.statement for constraint in modified.constraints}
    assert removed.statement in baseline_statements - modified_statements


def test_schema_describe_lists_nodes_and_relationships() -> None:
    schema = CDKOSchema.default()
    description = schema.describe()
    assert "nodes" in description and "relationships" in description
    assert "Document" in description["nodes"]
    assert "HAS_CHUNK" in description["relationships"]


def test_schema_introspection_returns_indexes_and_relationship_types() -> None:
    schema = CDKOSchema.default()
    introspection = schema.as_statements()
    assert "constraints" in introspection
    assert "indexes" in introspection
    assert "relationship_types" in introspection
    assert "HAS_CHUNK" in introspection["relationship_types"]
