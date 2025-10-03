# Add Knowledge Graph (Neo4j + CDKO-Med Schema)

## Why

A span-grounded, provenance-rich knowledge graph materializes medical entities, studies, evidence, and relationships in a queryable, navigable structure aligned with FHIR Evidence/EvidenceVariable semantics. CDKO-Med schema ensures interoperability and supports briefing outputs.

## What Changes

- Define Neo4j node labels & properties: :Document, :Chunk, :Study, :Arm, :Drug, :Device, :Procedure, :Condition, :Phenotype, :Outcome, :AdverseEvent, :EligibilityConstraint, :Evidence, :EvidenceVariable, :Identifier, :Organization, :ExtractionActivity (PROV)
- Create relationships: HAS_CHUNK, HAS_ARM, USES_INTERVENTION, ABOUT, MENTIONS (span-grounded), REPORTS, DEFINES, HAS_AE, HAS_ELIGIBILITY, HAS_IDENTIFIER, WAS_GENERATED_BY, SIMILAR_TO (optional)
- Implement constraints (uniqueness on uri, nct_id, rxcui, udi_di, loinc, doc_id, chunk_id)
- Create vector index chunk_qwen_idx (4096-D, cosine)
- Add MERGE-based write patterns (idempotent upserts with deterministic keys)
- Implement FHIR exporters (Evidence, EvidenceVariable resources with UCUM/LOINC/SNOMED codes)
- Add SHACL-style runtime checks (UCUM units, code presence, span integrity)
- Implement identity resolution (prefer MONDO for diseases, RxCUI for drugs, LOINC for labs; link conflicts via :SAME_AS)

## Impact

- **Affected specs**: NEW `knowledge-graph` capability
- **Affected code**: NEW `/kg/neo4j/constraints/`, `/kg/neo4j/writers/`, `/kg/neo4j/exporters/`, `/kg/neo4j/shacl/`
- **Dependencies**: Neo4j with APOC + n10s plugins; extractors (produce triples); Concept Catalog (for code validation)
- **Downstream**: Briefing outputs (query KG); FHIR exports; user dashboards
