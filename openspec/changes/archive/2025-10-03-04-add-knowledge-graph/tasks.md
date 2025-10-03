# Implementation Tasks

## 1. Schema Definition

- [x] 1.1 Define all node labels with required/optional properties (see proposal for full list)
- [x] 1.2 Define relationship types with properties (e.g., :MENTIONS {confidence, start, end, quote})
- [x] 1.3 Document property types (strings, integers, floats, arrays, maps, vector<4096>)

## 2. Constraints & Indexes

- [x] 2.1 CREATE CONSTRAINT doc_uri_unique FOR (d:Document) REQUIRE d.uri IS UNIQUE
- [x] 2.2 CREATE CONSTRAINT chunk_id_unique FOR (c:Chunk) REQUIRE c.id IS UNIQUE
- [x] 2.3 CREATE CONSTRAINT study_nct_unique FOR (s:Study) REQUIRE s.nct_id IS UNIQUE
- [x] 2.4 CREATE CONSTRAINT drug_rxcui_unique FOR (d:Drug) REQUIRE d.rxcui IS UNIQUE
- [x] 2.5 CREATE CONSTRAINT device_udi_unique FOR (x:Device) REQUIRE x.udi_di IS UNIQUE
- [x] 2.6 CREATE CONSTRAINT outcome_loinc_unique FOR (o:Outcome) REQUIRE o.loinc IS UNIQUE
- [x] 2.7 CREATE CONSTRAINT identifier_scheme_value_unique FOR (i:Identifier) REQUIRE (i.scheme, i.value) IS UNIQUE
- [x] 2.8 CREATE CONSTRAINT evidence_id_unique FOR (e:Evidence) REQUIRE e.id IS UNIQUE
- [x] 2.9 CREATE CONSTRAINT evvar_id_unique FOR (v:EvidenceVariable) REQUIRE v.id IS UNIQUE
- [x] 2.10 CREATE VECTOR INDEX chunk_qwen_idx FOR (c:Chunk) ON (c.embedding_qwen) OPTIONS {indexConfig: {`vector.dimensions`: 4096, `vector.similarity_function`: 'cosine'}}
- [x] 2.11 CREATE FULLTEXT INDEX chunk_text_ft ON NODE Chunk(text, path) OPTIONS {analyzer: 'english'}

## 3. Write Patterns (Idempotent MERGE)

- [x] 3.1 Implement Document write (MERGE on uri; SET meta, created_at, updated_at)
- [x] 3.2 Implement Chunk write (MERGE on id; SET text, facets, embeddings, splade_terms, model_meta)
- [x] 3.3 Implement EvidenceVariable write (MERGE on id; SET population_json, interventions_json, etc.; link to Document via :REPORTS)
- [x] 3.4 Implement Evidence write (MERGE on id; SET type, value, ci_low, ci_high, p_value, etc.; link to :Outcome and :EvidenceVariable)
- [x] 3.5 Implement AdverseEvent write (MERGE on pt_code or pt; link to :Study/:Arm via :HAS_AE with grade, count, denom)
- [x] 3.6 Implement Study/Arm/Intervention writes (MERGE on nct_id/arm_name/rxcui/udi_di)
- [x] 3.7 Implement EligibilityConstraint write (MERGE on id; SET type, logic_json, human_text; link to :Study)
- [x] 3.8 Implement ExtractionActivity write (MERGE on id; SET model, version, prompt_hash, schema_hash, ts)
- [x] 3.9 Link all assertions to :ExtractionActivity via :WAS_GENERATED_BY

## 4. SHACL-Style Runtime Checks

- [x] 4.1 UCUM validator (check :Outcome.unit_ucum, :Evidence.time_unit_ucum, facet:dose.unit against UCUM code list)
- [x] 4.2 Code presence validator (if :Evidence.outcome_loinc exists, ensure (:Evidence)-[:MEASURES]->(:Outcome{loinc}) exists)
- [x] 4.3 Span integrity validator (spans_json non-empty; start/end fit within originating chunk length)
- [x] 4.4 AE edge validator ((:Study)-[:HAS_AE]->(:AdverseEvent) must have count≥0, denom≥0, grade∈{1..5} if present)
- [x] 4.5 Provenance validator (:Evidence|:EvidenceVariable|:EligibilityConstraint must have ≥1 :WAS_GENERATED_BY edge)
- [x] 4.6 Dead-letter queue (kg_write_deadletter with reason, payload_hash for failed writes)

## 5. FHIR Exporters

- [x] 5.1 Implement EvidenceVariable exporter (populate characteristic[] with SNOMED/MONDO/HPO for population, RxNorm/UNII for interventions, LOINC for outcomes)
- [x] 5.2 Implement Evidence exporter (populate statistic with statisticType HR/RR/OR/MD/SMD, value, ci, pValue, sampleSize; certainty uses GRADE)
- [x] 5.3 Implement Provenance exporter (link to :ExtractionActivity → FHIR Provenance resource)
- [x] 5.4 Validate CodeableConcepts against Concept Lexicon
- [x] 5.5 Enforce UCUM in Evidence.statistic.attributeEstimate.unit

## 6. Identity Resolution & Crosswalks

- [x] 6.1 Use deterministic keys (NCT, RxCUI, UNII, LOINC, MedDRA are primary)
- [x] 6.2 Prefer MONDO for diseases, SNOMED second, ICD-11 third
- [x] 6.3 Do NOT auto-merge nodes with different primary codes; link via :SAME_AS with evidence (MONDO|UMLS|manual)
- [x] 6.4 Implement conflict detection (multiple nodes claiming same identity)

## 7. Batch Upserts (APOC)

- [x] 7.1 Use apoc.merge.node for bulk concept/chunk writes (batch size 1000)
- [x] 7.2 Use apoc.merge.relationship for bulk edge creation
- [x] 7.3 Set transaction limits (dbms.memory.transaction.max_size)

## 8. Optional: Navigation Edges

- [x] 8.1 Compute (:Chunk)-[:SIMILAR_TO {score, model_ver}]->(:Chunk) for adjacent or semantically similar chunks (optional; non-authoritative)
- [x] 8.2 Store only top-K=10 neighbors per chunk to limit graph size

## 9. Testing

- [x] 9.1 Unit tests for write patterns (MERGE idempotency; verify no duplicates)
- [x] 9.2 Integration tests (full pipeline → chunks → facets → extractors → KG write)
- [x] 9.3 Test SHACL validators (invalid UCUM → dead-letter; missing code → dead-letter)
- [x] 9.4 Test FHIR export (sample study → valid Evidence/EvidenceVariable resources; validate with HL7 validator)
- [x] 9.5 Test identity resolution (two sources for same drug → single :Drug node or linked via :SAME_AS)

## 10. Documentation

- [x] 10.1 Document CDKO-Med schema with examples
- [x] 10.2 Create KG query cookbook (Cypher examples for common queries)
- [x] 10.3 Write FHIR export runbook
- [x] 10.4 Document SHACL validation rules and failure handling
