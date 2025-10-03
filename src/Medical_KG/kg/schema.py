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
    """In-memory representation of the CDKO-Med graph schema."""

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
                    NodeProperty(
                        "uri", "string", required=True, description="Canonical document URI"
                    ),
                    NodeProperty(
                        "id", "string", required=True, description="Internal document identifier"
                    ),
                    NodeProperty("source", "string", description="Ingestion source"),
                    NodeProperty("title", "string", description="Document title"),
                    NodeProperty("language", "string", description="ISO 639-1 language code"),
                    NodeProperty("publication_date", "date", description="Publication date"),
                    NodeProperty("meta", "map", description="Arbitrary metadata map"),
                    NodeProperty("created_at", "datetime", description="Creation timestamp"),
                    NodeProperty("updated_at", "datetime", description="Last update timestamp"),
                ],
            ),
            "Chunk": NodeSchema(
                label="Chunk",
                properties=[
                    NodeProperty("id", "string", required=True, description="Chunk identifier"),
                    NodeProperty("doc_uri", "string", description="Parent document URI"),
                    NodeProperty("text", "string", description="Chunk text"),
                    NodeProperty("intent", "string", description="Author intent classification"),
                    NodeProperty("section", "string", description="Source section label"),
                    NodeProperty("start", "integer", description="Character start offset"),
                    NodeProperty("end", "integer", description="Character end offset"),
                    NodeProperty("token_count", "integer", description="Token length"),
                    NodeProperty(
                        "coherence_score", "float", description="Model-estimated coherence"
                    ),
                    NodeProperty("facets", "map", description="Facet assignments"),
                    NodeProperty("embedding_qwen", "vector<4096>", description="Qwen embedding"),
                    NodeProperty("splade_terms", "map", description="SPLADE sparse vector"),
                    NodeProperty("model_meta", "map", description="Embedding model metadata"),
                ],
            ),
            "Concept": NodeSchema(
                label="Concept",
                properties=[
                    NodeProperty("iri", "string", required=True, description="Concept IRI"),
                    NodeProperty("codes", "array", description="List of system|code identifiers"),
                    NodeProperty("label", "string", description="Preferred label"),
                    NodeProperty("definition", "string", description="Canonical definition"),
                    NodeProperty("synonyms", "array", description="Synonym labels"),
                    NodeProperty("ontology", "string", description="Source ontology identifier"),
                    NodeProperty("semantic_types", "array", description="Semantic type hints"),
                    NodeProperty("license_bucket", "string", description="License restrictions"),
                    NodeProperty("embedding_qwen", "vector<4096>", description="Concept embedding"),
                ],
            ),
            "Study": NodeSchema(
                label="Study",
                properties=[
                    NodeProperty(
                        "nct_id",
                        "string",
                        required=True,
                        description="ClinicalTrials.gov identifier",
                    ),
                    NodeProperty("title", "string", description="Study title"),
                    NodeProperty("phase", "string", description="Study phase"),
                    NodeProperty("status", "string", description="Recruitment status"),
                    NodeProperty("conditions", "array", description="Study conditions"),
                    NodeProperty(
                        "interventions_json", "map", description="Structured interventions"
                    ),
                    NodeProperty("arms_json", "map", description="Structured arms"),
                    NodeProperty("eligibility_json", "map", description="Eligibility criteria"),
                ],
            ),
            "Arm": NodeSchema(
                label="Arm",
                properties=[
                    NodeProperty("id", "string", required=True, description="Arm identifier"),
                    NodeProperty("label", "string", description="Arm label"),
                    NodeProperty("type", "string", description="Arm type"),
                    NodeProperty("n_enrolled", "integer", description="Enrollment count"),
                    NodeProperty(
                        "intervention_summary",
                        "string",
                        description="Text summary of interventions",
                    ),
                ],
            ),
            "Intervention": NodeSchema(
                label="Intervention",
                properties=[
                    NodeProperty(
                        "id", "string", required=True, description="Intervention identifier"
                    ),
                    NodeProperty("name", "string", description="Display name"),
                    NodeProperty("type", "string", description="Intervention category"),
                    NodeProperty("rxcui", "string", description="RxNorm code"),
                    NodeProperty("unii", "string", description="UNII ingredient code"),
                    NodeProperty("udi_di", "string", description="Device identifier"),
                ],
            ),
            "Outcome": NodeSchema(
                label="Outcome",
                properties=[
                    NodeProperty("id", "string", required=True, description="Outcome identifier"),
                    NodeProperty("name", "string", description="Outcome label"),
                    NodeProperty("description", "string", description="Outcome description"),
                    NodeProperty("loinc", "string", description="LOINC code"),
                    NodeProperty("unit_ucum", "string", description="UCUM unit"),
                ],
            ),
            "EvidenceVariable": NodeSchema(
                label="EvidenceVariable",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("population_json", "map", description="Population definition"),
                    NodeProperty(
                        "interventions_json", "map", description="Intervention definition"
                    ),
                    NodeProperty("comparators_json", "map", description="Comparator definition"),
                    NodeProperty("outcomes_json", "map", description="Outcome definition"),
                    NodeProperty("timeframe", "string", description="Observation timeframe"),
                    NodeProperty("spans_json", "array", description="Supporting spans"),
                    NodeProperty("provenance", "array", description="Extraction provenance"),
                ],
            ),
            "Evidence": NodeSchema(
                label="Evidence",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("type", "string", description="Statistic type (HR/RR/OR/etc.)"),
                    NodeProperty("value", "float", description="Point estimate"),
                    NodeProperty("ci_low", "float", description="Confidence interval low"),
                    NodeProperty("ci_high", "float", description="Confidence interval high"),
                    NodeProperty("p_value", "float", description="P value"),
                    NodeProperty("n_total", "integer", description="Sample size"),
                    NodeProperty("time_unit_ucum", "string", description="Time unit UCUM code"),
                    NodeProperty("certainty", "string", description="GRADE certainty"),
                    NodeProperty("model", "string", description="Extraction model"),
                    NodeProperty("outcome_loinc", "string", description="Linked outcome LOINC"),
                    NodeProperty("spans_json", "array", description="Supporting spans"),
                    NodeProperty("provenance", "array", description="Provenance references"),
                ],
            ),
            "AdverseEvent": NodeSchema(
                label="AdverseEvent",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("term", "string", description="Reported term"),
                    NodeProperty("meddra_pt", "string", description="MedDRA preferred term"),
                    NodeProperty("grade", "integer", description="CTCAE grade"),
                    NodeProperty("count", "integer", description="Event count"),
                    NodeProperty("denominator", "integer", description="Population denominator"),
                    NodeProperty("arm", "string", description="Arm identifier"),
                    NodeProperty("serious", "boolean", description="Serious adverse event flag"),
                    NodeProperty("onset_days", "float", description="Onset latency"),
                    NodeProperty("spans_json", "array", description="Supporting spans"),
                    NodeProperty("provenance", "array", description="Provenance references"),
                ],
            ),
            "EligibilityConstraint": NodeSchema(
                label="EligibilityConstraint",
                properties=[
                    NodeProperty("id", "string", required=True),
                    NodeProperty("type", "string", description="Inclusion or exclusion"),
                    NodeProperty("logic_json", "map", description="Structured eligibility logic"),
                    NodeProperty("human_text", "string", description="Canonical text"),
                    NodeProperty("spans_json", "array", description="Supporting spans"),
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
            "Drug": NodeSchema(
                label="Drug",
                properties=[
                    NodeProperty("rxcui", "string", required=True, description="RxNorm code"),
                    NodeProperty("name", "string", description="Drug name"),
                    NodeProperty("synonyms", "array", description="Drug synonyms"),
                    NodeProperty("unii", "string", description="UNII ingredient code"),
                ],
            ),
            "Device": NodeSchema(
                label="Device",
                properties=[
                    NodeProperty("udi_di", "string", required=True, description="UDI-DI"),
                    NodeProperty("brand", "string", description="Brand name"),
                    NodeProperty("model", "string", description="Model identifier"),
                    NodeProperty("company", "string", description="Manufacturer"),
                ],
            ),
            "Identifier": NodeSchema(
                label="Identifier",
                properties=[
                    NodeProperty(
                        "scheme", "string", required=True, description="Identifier scheme"
                    ),
                    NodeProperty("value", "string", required=True, description="Identifier value"),
                    NodeProperty("label", "string", description="Human readable label"),
                    NodeProperty("version", "string", description="Scheme version"),
                ],
            ),
        }

        relationships = {
            "HAS_CHUNK": RelationshipSchema(
                type="HAS_CHUNK",
                start="Document",
                end="Chunk",
                properties=[
                    NodeProperty("order", "integer", description="Chunk order within document")
                ],
            ),
            "MENTIONS": RelationshipSchema(
                type="MENTIONS",
                start="Chunk",
                end="Concept",
                properties=[
                    NodeProperty("confidence", "float", description="Extractor confidence"),
                    NodeProperty("start", "integer", description="Start offset"),
                    NodeProperty("end", "integer", description="End offset"),
                    NodeProperty("quote", "string", description="Surface form"),
                    NodeProperty("negated", "boolean", description="Negation flag"),
                    NodeProperty("hypothetical", "boolean", description="Hypothetical flag"),
                ],
            ),
            "HAS_IDENTIFIER": RelationshipSchema(
                type="HAS_IDENTIFIER",
                start="Document",
                end="Identifier",
                properties=[],
            ),
            "DESCRIBES": RelationshipSchema(
                type="DESCRIBES",
                start="Document",
                end="Study",
                properties=[],
            ),
            "HAS_ARM": RelationshipSchema("HAS_ARM", "Study", "Arm"),
            "USES_INTERVENTION": RelationshipSchema(
                type="USES_INTERVENTION",
                start="Arm",
                end="Intervention",
                properties=[
                    NodeProperty("dose", "map", description="Dose metadata including UCUM unit")
                ],
            ),
            "HAS_OUTCOME": RelationshipSchema(
                type="HAS_OUTCOME",
                start="Study",
                end="Outcome",
                properties=[NodeProperty("timeframe", "string", description="Outcome timeframe")],
            ),
            "REPORTS": RelationshipSchema(
                type="REPORTS",
                start="Study",
                end="Evidence",
                properties=[],
            ),
            "DERIVES_FROM": RelationshipSchema("DERIVES_FROM", "Evidence", "EvidenceVariable"),
            "MEASURES": RelationshipSchema(
                type="MEASURES",
                start="Evidence",
                end="Outcome",
                properties=[
                    NodeProperty("confidence", "float", description="Extractor confidence")
                ],
            ),
            "HAS_AE": RelationshipSchema(
                type="HAS_AE",
                start="Study",
                end="AdverseEvent",
                properties=[
                    NodeProperty("count", "integer", description="Event count"),
                    NodeProperty("denominator", "integer", description="Population denominator"),
                    NodeProperty("grade", "integer", description="Worst grade"),
                ],
            ),
            "HAS_ELIGIBILITY": RelationshipSchema(
                "HAS_ELIGIBILITY", "Study", "EligibilityConstraint"
            ),
            "WAS_GENERATED_BY": RelationshipSchema(
                "WAS_GENERATED_BY", "Evidence", "ExtractionActivity"
            ),
            "WAS_GENERATED_BY_VAR": RelationshipSchema(
                "WAS_GENERATED_BY_VAR", "EvidenceVariable", "ExtractionActivity"
            ),
            "WAS_GENERATED_BY_ELIG": RelationshipSchema(
                "WAS_GENERATED_BY_ELIG", "EligibilityConstraint", "ExtractionActivity"
            ),
            "SAME_AS": RelationshipSchema("SAME_AS", "Concept", "Concept"),
            "IS_A": RelationshipSchema("IS_A", "Concept", "Concept"),
            "SIMILAR_TO": RelationshipSchema(
                type="SIMILAR_TO",
                start="Chunk",
                end="Chunk",
                properties=[
                    NodeProperty("score", "float", description="Similarity score"),
                    NodeProperty("model_ver", "string", description="Embedding model version"),
                ],
            ),
        }

        constraints = [
            Constraint(
                "CREATE CONSTRAINT doc_uri_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.uri IS UNIQUE",
                "Unique constraint on Document.uri",
            ),
            Constraint(
                "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
                "Unique constraint on Chunk.id",
            ),
            Constraint(
                "CREATE CONSTRAINT study_nct_unique IF NOT EXISTS FOR (s:Study) REQUIRE s.nct_id IS UNIQUE",
                "Unique constraint on Study.nct_id",
            ),
            Constraint(
                "CREATE CONSTRAINT drug_rxcui_unique IF NOT EXISTS FOR (d:Drug) REQUIRE d.rxcui IS UNIQUE",
                "Unique constraint on Drug.rxcui",
            ),
            Constraint(
                "CREATE CONSTRAINT device_udi_unique IF NOT EXISTS FOR (x:Device) REQUIRE x.udi_di IS UNIQUE",
                "Unique constraint on Device.udi_di",
            ),
            Constraint(
                "CREATE CONSTRAINT outcome_loinc_unique IF NOT EXISTS FOR (o:Outcome) REQUIRE o.loinc IS UNIQUE",
                "Unique constraint on Outcome.loinc",
            ),
            Constraint(
                "CREATE CONSTRAINT identifier_scheme_value_unique IF NOT EXISTS FOR (i:Identifier) REQUIRE (i.scheme, i.value) IS UNIQUE",
                "Composite uniqueness for Identifier",
            ),
            Constraint(
                "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE",
                "Unique constraint on Evidence.id",
            ),
            Constraint(
                "CREATE CONSTRAINT evvar_id_unique IF NOT EXISTS FOR (v:EvidenceVariable) REQUIRE v.id IS UNIQUE",
                "Unique constraint on EvidenceVariable.id",
            ),
        ]

        indexes = [
            Index(
                "CREATE INDEX doc_source_pubdate_idx IF NOT EXISTS FOR (d:Document) ON (d.source, d.publication_date)",
                "Composite index for Document source/date queries",
            ),
            Index(
                "CREATE INDEX chunk_intent_idx IF NOT EXISTS FOR (c:Chunk) ON (c.intent)",
                "Property index for chunk intent",
            ),
            Index(
                "CREATE INDEX chunk_section_idx IF NOT EXISTS FOR (c:Chunk) ON (c.section)",
                "Property index for chunk section",
            ),
            Index(
                "CREATE INDEX chunk_doc_uri_idx IF NOT EXISTS FOR (c:Chunk) ON (c.doc_uri)",
                "Lookup index for chunk to document joins",
            ),
            Index(
                "CREATE VECTOR INDEX chunk_qwen_idx IF NOT EXISTS FOR (c:Chunk) ON (c.embedding_qwen) OPTIONS {indexConfig: {`vector.dimensions`: 4096, `vector.similarity_function`: 'cosine'}}",
                "Vector index for chunk embeddings",
            ),
            Index(
                "CREATE VECTOR INDEX concept_qwen_idx IF NOT EXISTS FOR (c:Concept) ON (c.embedding_qwen) OPTIONS {indexConfig: {`vector.dimensions`: 4096, `vector.similarity_function`: 'cosine'}}",
                "Vector index for concept embeddings",
            ),
            Index(
                "CREATE FULLTEXT INDEX chunk_text_ft IF NOT EXISTS FOR (c:Chunk) ON EACH [c.text, c.path] OPTIONS {analyzer: 'english'}",
                "Full-text index for chunk text",
            ),
        ]

        return cls(
            nodes=nodes, relationships=relationships, constraints=constraints, indexes=indexes
        )

    def describe(self) -> Mapping[str, object]:
        return {
            "nodes": {label: schema.as_dict() for label, schema in self.nodes.items()},
            "relationships": {
                rtype: schema.as_dict() for rtype, schema in self.relationships.items()
            },
            "constraints": [constraint.statement for constraint in self.constraints],
            "indexes": [index.statement for index in self.indexes],
        }

    def as_statements(self) -> Mapping[str, List[str]]:
        """Return Cypher statements for constraints and indexes."""

        return {
            "constraints": [constraint.statement for constraint in self.constraints],
            "indexes": [index.statement for index in self.indexes],
            "node_indexes": [schema.label for schema in self.nodes.values() if schema.properties],
            "relationship_types": list(self.relationships.keys()),
        }
