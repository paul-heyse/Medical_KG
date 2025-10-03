# CDKO-Med Knowledge Graph Guide

## Schema Summary

The schema defined in `src/Medical_KG/kg/schema.py` introduces:

- **Nodes** – `Document`, `Chunk`, `Concept`, `Study`, `Arm`, `Intervention`, `Outcome`, `Evidence`, `EvidenceVariable`, `AdverseEvent`, `EligibilityConstraint`, `ExtractionActivity`, `Drug`, `Device`, and `Identifier`.
- **Relationships** – `HAS_CHUNK`, `MENTIONS`, `HAS_IDENTIFIER`, `DESCRIBES`, `HAS_ARM`, `USES_INTERVENTION`, `HAS_OUTCOME`, `REPORTS`, `DERIVES_FROM`, `MEASURES`, `HAS_AE`, `HAS_ELIGIBILITY`, `WAS_GENERATED_BY*`, `SAME_AS`, `IS_A`, and `SIMILAR_TO`.
- **Constraints** – uniqueness for document URIs, chunk IDs, study NCT IDs, drug RxCUIs, device UDI-DIs, outcome LOINCs, identifier (scheme,value) pairs, evidence IDs, and evidence variable IDs.
- **Indexes** – property indexes for chunk intent/section/doc_uri, composite `Document(source, publication_date)`, vector indexes on chunk and concept embeddings, and a chunk full-text index.

### Example Nodes

```cypher
MERGE (d:Document {uri: 'doc://pmc/12345', id: 'pmc#12345'})
  SET d += {source: 'pmc', title: 'Study of Lactate', language: 'en', publication_date: date('2024-01-01')};

MERGE (c:Chunk {id: 'chunk#1'})
  SET c += {doc_uri: d.uri, text: 'Lactate improves outcomes.', intent: 'evidence', start: 0, end: 28};

MERGE (o:Outcome {id: 'outcome#1', name: 'Mortality', loinc: '1234-5', unit_ucum: '1'});
```

## Query Cookbook

Find evidence for a given drug in a condition:

```cypher
MATCH (:Concept {label: $drug})<-[:MENTIONS]-(chunk:Chunk)
MATCH (chunk)<-[:HAS_CHUNK]-(doc:Document)
MATCH (doc)-[:REPORTS]->(e:Evidence)-[:MEASURES]->(o:Outcome)
MATCH (:Concept {label: $condition})<-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(doc)
RETURN e.id, o.name, e.value, e.ci_low, e.ci_high;
```

Traverse disease hierarchies using `SAME_AS` / ontology edges:

```cypher
MATCH (d:Concept {iri: $root})-[:SAME_AS|:IS_A*0..]->(descendant)
MATCH (descendant)<-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(doc:Document)-[:REPORTS]->(e:Evidence)
RETURN descendant.iri, e.id;
```

### Programmatic helpers

`KgQueryApi` (`src/Medical_KG/kg/query.py`) provides parameterised builders for these patterns:

```python
from Medical_KG.kg.query import KgQueryApi

api = KgQueryApi()
related = api.related_evidence(drug_label="Warfarin", condition_label="Atrial fibrillation")
vector = api.vector_search(index_name="chunk_qwen_idx", query_vector=[0.1, 0.2, 0.3])
```

Execute the returned `Query.cypher` with its `Query.parameters` using the Neo4j driver to avoid manual string templating.

Trace provenance:

```cypher
MATCH (e:Evidence {id: $evidence_id})-[:WAS_GENERATED_BY]->(activity:ExtractionActivity)
RETURN activity.model, activity.version, activity.timestamp;
```

## FHIR Export Runbook

Use `EvidenceExporter` (`src/Medical_KG/kg/fhir.py`) to materialise FHIR resources:

```python
from Medical_KG.kg.fhir import EvidenceExporter

exporter = EvidenceExporter(ucum_codes={'mg', '1'})
resource = exporter.export_evidence(evidence_node)
```

- Evidence resources include statistic blocks with point estimate, confidence interval, UCUM unit, and sample size.
- EvidenceVariable resources validate `ConceptLexicon` membership for SNOMED/MONDO/HPO concepts.
- Provenance resources tie `ExtractionActivity` metadata to generated Evidence/EvidenceVariable resources.

Validate generated bundles using the HL7 validator or the official FHIR CLI before downstream submission.

## SHACL-Style Validation

`KgValidator` performs runtime checks equivalent to SHACL shapes:

1. **UCUM codes** – verifies `Evidence.unit_ucum`, `Evidence.time_unit_ucum`, `Outcome.unit_ucum`, and `dose.unit` values.
2. **Code presence** – ensures that any `Evidence.outcome_loinc` aligns with a `MEASURES` relationship to a matching `Outcome` node.
3. **Span integrity** – confirms `spans_json` arrays are non-empty with non-negative offsets.
4. **Adverse event edges** – enforces non-negative counts/denominators and grade in `{1..5}`.
5. **Provenance** – requires `provenance` arrays on Evidence, EvidenceVariable, and EligibilityConstraint nodes.
6. **Identity conflicts** – dead-letters duplicate deterministic keys (NCT IDs, RxCUIs, UDI-DIs, LOINCs, Concept IRIs).

Failures are routed to `DeadLetterQueue`, producing hashes suitable for triage and replay.
