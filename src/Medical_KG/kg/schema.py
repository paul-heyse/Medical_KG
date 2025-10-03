from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping


@dataclass(slots=True)
class NodeProperty:
    name: str
    type: str
    required: bool = False
    description: str = ""


@dataclass(slots=True)
class NodeSchema:
    label: str
    properties: List[NodeProperty] = field(default_factory=list)

    def required_properties(self) -> List[NodeProperty]:
        return [prop for prop in self.properties if prop.required]

    def optional_properties(self) -> List[NodeProperty]:
        return [prop for prop in self.properties if not prop.required]

    def as_dict(self) -> Dict[str, List[Dict[str, str]]]:
        return {
            "required": [
                {"name": prop.name, "type": prop.type, "description": prop.description}
                for prop in self.required_properties()
            ],
            "optional": [
                {"name": prop.name, "type": prop.type, "description": prop.description}
                for prop in self.optional_properties()
            ],
        }


@dataclass(slots=True)
class RelationshipSchema:
    type: str
    start: str
    end: str
    properties: List[NodeProperty] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "start": self.start,
            "end": self.end,
            "properties": [
                {"name": prop.name, "type": prop.type, "description": prop.description}
                for prop in self.properties
            ],
        }


@dataclass(slots=True)
class Constraint:
    statement: str
    description: str


@dataclass(slots=True)
class Index:
    statement: str
    description: str


@dataclass(slots=True)
class CDKOSchema:
    nodes: Dict[str, NodeSchema] = field(default_factory=dict)
    relationships: Dict[str, RelationshipSchema] = field(default_factory=dict)
    constraints: List[Constraint] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)

    @classmethod
    def default(cls) -> "CDKOSchema":
        nodes = {
            "Document": NodeSchema(
                label="Document",
                properties=[
                    NodeProperty("uri", "string", required=True, description="Canonical document URI"),
                    NodeProperty("id", "string", required=True, description="Internal document identifier"),
                    NodeProperty("source", "string", description="Ingestion source"),
                    NodeProperty("title", "string", description="Document title"),
                    NodeProperty("language", "string", description="ISO 639-1 code"),
                    NodeProperty("meta", "map", description="Arbitrary metadata"),
                    NodeProperty("created_at", "datetime", description="Ingestion timestamp"),
                ],
            ),
            "Chunk": NodeSchema(
                label="Chunk",
                properties=[
                    NodeProperty("id", "string", required=True, description="Chunk identifier"),
                    NodeProperty("text", "string", description="Chunk text"),
                    NodeProperty("path", "string", description="Section path"),
                    NodeProperty("embedding_qwen", "vector<4096>", description="Qwen embedding"),
                    NodeProperty("splade_terms", "map", description="SPLADE term weights"),
                    NodeProperty("model_meta", "map", description="Embedding metadata"),
                ],
            ),
            "Study": NodeSchema(
                label="Study",
                properties=[
                    NodeProperty("nct_id", "string", required=True, description="ClinicalTrials.gov identifier"),
                    NodeProperty("title", "string", description="Study title"),
                    NodeProperty("status", "string", description="Recruitment status"),
                ],
            ),
            "Arm": NodeSchema(
                label="Arm",
                properties=[
                    NodeProperty("name", "string", required=True, description="Arm name"),
                    NodeProperty("type", "string", description="Arm type"),
                ],
            ),
            "Intervention": NodeSchema(
                label="Intervention",
                properties=[
                    NodeProperty("id", "string", required=True, description="Intervention identifier"),
                    NodeProperty("name", "string", description="Display name"),
                    NodeProperty("rxcui", "string", description="RxNorm identifier"),
                    NodeProperty("udi_di", "string", description="Device identifier"),
                ],
            ),
            "Outcome": NodeSchema(
                label="Outcome",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("name", "string", description="Outcome label"),
                    NodeProperty("loinc", "string", description="LOINC code"),
                    NodeProperty("unit_ucum", "string", description="UCUM unit"),
                ],
            ),
            "EvidenceVariable": NodeSchema(
                label="EvidenceVariable",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("population_json", "map", description="Population definition"),
                    NodeProperty("interventions_json", "map", description="Interventions definition"),
                    NodeProperty("comparators_json", "map", description="Comparators definition"),
                ],
            ),
            "Evidence": NodeSchema(
                label="Evidence",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("type", "string", description="Statistic type"),
                    NodeProperty("value", "float", description="Point estimate"),
                    NodeProperty("ci_low", "float", description="Lower CI"),
                    NodeProperty("ci_high", "float", description="Upper CI"),
                    NodeProperty("p_value", "float", description="P value"),
                    NodeProperty("spans_json", "array", description="Supporting spans"),
                    NodeProperty("provenance", "array", description="Extraction provenance"),
                ],
            ),
            "AdverseEvent": NodeSchema(
                label="AdverseEvent",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("pt_code", "string", description="MedDRA preferred term"),
                    NodeProperty("grade", "integer", description="Grade"),
                ],
            ),
            "EligibilityConstraint": NodeSchema(
                label="EligibilityConstraint",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("type", "string", description="Inclusion or exclusion"),
                    NodeProperty("logic_json", "map", description="Structured logic"),
                    NodeProperty("human_text", "string", description="Canonical text"),
                    NodeProperty("provenance", "array", description="Extraction provenance"),
                ],
            ),
            "ExtractionActivity": NodeSchema(
                label="ExtractionActivity",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("model", "string", description="Extractor model"),
                    NodeProperty("version", "string", description="Model version"),
                    NodeProperty("prompt_hash", "string", description="Prompt hash"),
                    NodeProperty("schema_hash", "string", description="Schema hash"),
                    NodeProperty("timestamp", "datetime", description="Extraction timestamp"),
                ],
            ),
        }

        relationships = {
            "HAS_CHUNK": RelationshipSchema(
                type="HAS_CHUNK",
                start="Document",
                end="Chunk",
                properties=[NodeProperty("order", "integer", description="Chunk order")],
            ),
            "HAS_ARM": RelationshipSchema("HAS_ARM", "Study", "Arm"),
            "USES_INTERVENTION": RelationshipSchema(
                type="USES_INTERVENTION",
                start="Arm",
                end="Intervention",
                properties=[NodeProperty("dose", "map", description="Dosing information")],
            ),
            "HAS_OUTCOME": RelationshipSchema(
                type="HAS_OUTCOME",
                start="Study",
                end="Outcome",
                properties=[NodeProperty("timeframe", "string", description="Outcome timeframe")],
            ),
            "REPORTS": RelationshipSchema("REPORTS", "EvidenceVariable", "Document"),
            "MEASURES": RelationshipSchema(
                type="MEASURES",
                start="Evidence",
                end="Outcome",
                properties=[NodeProperty("confidence", "float", description="Model confidence")],
            ),
            "DERIVES_FROM": RelationshipSchema("DERIVES_FROM", "Evidence", "EvidenceVariable"),
            "HAS_AE": RelationshipSchema(
                type="HAS_AE",
                start="Study",
                end="AdverseEvent",
                properties=[
                    NodeProperty("count", "integer", description="Number of events"),
                    NodeProperty("denominator", "integer", description="Sample size"),
                    NodeProperty("grade", "integer", description="Worst grade"),
                ],
            ),
            "SATISFIES": RelationshipSchema("SATISFIES", "EligibilityConstraint", "Study"),
            "WAS_GENERATED_BY": RelationshipSchema("WAS_GENERATED_BY", "Evidence", "ExtractionActivity"),
        }

        constraints = [
            Constraint("CREATE CONSTRAINT doc_uri_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.uri IS UNIQUE", "Unique document URIs"),
            Constraint("CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE", "Chunk id uniqueness"),
            Constraint("CREATE CONSTRAINT study_nct_unique IF NOT EXISTS FOR (s:Study) REQUIRE s.nct_id IS UNIQUE", "Study id uniqueness"),
            Constraint("CREATE CONSTRAINT outcome_loinc_unique IF NOT EXISTS FOR (o:Outcome) REQUIRE o.loinc IS UNIQUE", "Outcome LOINC uniqueness"),
            Constraint("CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE", "Evidence id uniqueness"),
            Constraint("CREATE CONSTRAINT evvar_id_unique IF NOT EXISTS FOR (v:EvidenceVariable) REQUIRE v.id IS UNIQUE", "Evidence variable id uniqueness"),
        ]

        indexes = [
            Index(
                "CREATE VECTOR INDEX chunk_qwen_idx IF NOT EXISTS FOR (c:Chunk) ON (c.embedding_qwen) OPTIONS {indexConfig: {`vector.dimensions`: 4096, `vector.similarity_function`: 'cosine'}}",
                "Chunk embedding vector index",
            ),
            Index(
                "CREATE FULLTEXT INDEX chunk_text_ft IF NOT EXISTS FOR (n:Chunk) ON EACH [n.text] OPTIONS {analyzer: 'english'}",
                "Chunk full text index",
            ),
        ]

        return cls(nodes=nodes, relationships=relationships, constraints=constraints, indexes=indexes)

    def describe(self) -> Mapping[str, object]:
        return {
            "nodes": {label: schema.as_dict() for label, schema in self.nodes.items()},
            "relationships": {rtype: schema.as_dict() for rtype, schema in self.relationships.items()},
            "constraints": [constraint.statement for constraint in self.constraints],
            "indexes": [index.statement for index in self.indexes],
        }
