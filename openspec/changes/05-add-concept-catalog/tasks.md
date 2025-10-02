# Implementation Tasks

## 1. Concept Data Model & Schema

- [x] 1.1 Define concept.schema.json (iri, family, label, preferred_term, synonyms[], definition, codes[], xrefs[], hierarchy, attributes, embedding_qwen, splade_terms, release, license_bucket, provenance)
- [x] 1.2 Define family enum (condition, phenotype, lab, drug, substance, outcome, adverse_event, device, literature_id)
- [x] 1.3 Define synonym types (exact, narrow, broad, related, brand, abbrev)

## 2. Ontology Loaders

- [x] 2.1 SNOMED CT loader (RF2 files; concepts, descriptions, relationships; build IS_A hierarchy)
- [x] 2.2 ICD-11 loader (WHO API; OAuth2; entity retrieval with parents/children)
- [x] 2.3 MONDO loader (OWL/JSON; disease ontology; xrefs to ICD/SNOMED/OMIM)
- [x] 2.4 HPO loader (OBO/TSV; phenotypes; disease associations)
- [x] 2.5 LOINC loader (CSV/REL; components, properties, methods; UCUM units mapping)
- [x] 2.6 RxNorm loader (RRF files; ingredients, brands, clinical drugs; TTY hierarchy)
- [x] 2.7 UNII/GSRS loader (JSON; substances; FDA registry)
- [x] 2.8 MedDRA loader (MDB/CSV; PTs, LLTs, SOCs; quarterly releases; license-gated)
- [x] 2.9 CTCAE loader (PDF/Excel; grades 1-5 mapping to MedDRA)
- [x] 2.10 AccessGUDID loader (CSV/API; UDI-DI, brand, model, attributes)
- [x] 2.11 ID validators (NCT regex; PMID/PMCID numeric; DOI 10.xxxx; LOINC N-D; SNOMED Verhoeff; GTIN-14 mod-10)

## 3. Text Normalization & Cross-walks

- [x] 3.1 Normalize text (Unicode NFC, lowercase for matching, preserve display case)
- [x] 3.2 Normalize Greek letters (α→alpha), chemical salts (recognize but keep in display)
- [x] 3.3 Handle US/UK spellings (anemia/anaemia), plurals (lemmatize)
- [x] 3.4 Build MONDO bridges for disease mappings
- [x] 3.5 Use UMLS CUIs for crosswalks (when licensed)
- [x] 3.6 Mark license_bucket (open, permissive, restricted, proprietary) per concept

## 4. Embeddings & SPLADE

- [x] 4.1 Compute SPLADE doc-side expansion (tokenize with model tokenizer; top-K=200 terms per concept)
- [x] 4.2 Compute Qwen dense vectors (input: label + top-8 synonyms + definition ≤256 tokens; 4096-D)
- [x] 4.3 Batch embeddings (256 concepts/batch; adjust to VRAM)
- [x] 4.4 Dedup identical label+definition across ontologies (compute once, share vectors)

## 5. Neo4j Integration

- [ ] 5.1 Create :Concept nodes with labels :Condition|:Phenotype|:Lab|:Drug|:Substance|:Outcome|:AdverseEvent|:Device
- [ ] 5.2 Create (:Concept)-[:IS_A]->(:Concept) for taxonomy
- [ ] 5.3 Create (:Concept)-[:SAME_AS]->(:Concept) for crosswalks
- [ ] 5.4 Create constraints (concept_iri_unique)
- [ ] 5.5 Create vector index concept_qwen_idx (4096-D, cosine)

## 6. OpenSearch Index

- [ ] 6.1 Create concepts_v1 index with mappings (iri keyword, family keyword, label text, synonyms nested, definition text, codes nested, splade_terms rank_features)
- [ ] 6.2 Configure biomed analyzer (synonym_graph filter with analysis/biomed_synonyms.txt generated from catalog)
- [ ] 6.3 Set field boosts (label^3, synonyms.value^2, definition^0.5)
- [ ] 6.4 Bulk index all concepts

## 7. Catalog Build Pipeline

- [x] 7.1 Implement DAG: download → parse → normalize → enrich → merge → embed → write
- [x] 7.2 Generate catalog release hash (SHA256 of concatenated source versions)
- [x] 7.3 Write provenance (pipeline_ver, ingested_at, source_uri)
- [ ] 7.4 Implement idempotency (skip if release hash unchanged)

## 8. License Gating & ACLs

- [ ] 8.1 Read licenses.yml on startup (SNOMED, UMLS, MedDRA flags)
- [ ] 8.2 Disable loaders if license missing/invalid
- [x] 8.3 Filter query results (exclude restricted labels/definitions if caller lacks entitlement)
- [x] 8.4 Audit log (every EL or extraction write includes user/service, model, version, timestamp)

## 9. Updater Service

- [ ] 9.1 Define cron schedules (SNOMED quarterly, ICD-11 biannual, MONDO/HPO monthly, RxNorm weekly, GUDID every 6 hours)
- [ ] 9.2 Implement differential updates (compare release versions; reindex only changed concepts)
- [ ] 9.3 Regenerate biomed_synonyms.txt on catalog refresh
- [ ] 9.4 Rolling restart OpenSearch analyzers after synonym update

## 10. Testing

- [x] 10.1 Unit tests for each loader (sample inputs → expected Concept objects)
- [x] 10.2 Unit tests for ID validators (positive/negative test sets)
- [ ] 10.3 Integration test (full catalog build → Neo4j + OpenSearch + FAISS)
- [x] 10.4 Test license enforcement (query with/without entitlements; verify redaction)
- [ ] 10.5 Test crosswalks (MONDO → ICD-11/SNOMED; UMLS CUI → all source codes)

## 11. Documentation

- [ ] 11.1 Document how to acquire licenses (SNOMED affiliate, UMLS acceptance, MedDRA subscription)
- [ ] 11.2 Create catalog refresh runbook
- [ ] 11.3 Document synonym file generation and analyzer reload procedure
