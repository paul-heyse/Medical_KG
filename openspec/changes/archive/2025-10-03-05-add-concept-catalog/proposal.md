# Add Concept Catalog (Ontologies & Terminologies)

## Why

Unified concept catalog spanning diseases, phenotypes, labs, drugs, adverse events, and devices enables high-recall candidate generation for entity linking, ontology-aware queries, semantic boosts, and crosswalk mappings. Must support versioning, licensing enforcement, and three retrieval modalities (lexical/BM25, sparse/SPLADE, dense/vector).

## What Changes

- Create unified Concept data model (JSON Schema) with iri, family, label, preferred_term, synonyms[], definition, codes[], xrefs[], hierarchy (parents/ancestors), attributes, embeddings (qwen/splade), release metadata, license_bucket
- Implement loaders for all ontologies: SNOMED CT, ICD-11, MONDO, HPO, LOINC (+UCUM), RxNorm, UNII/GSRS, MedDRA (+CTCAE), AccessGUDID, NCT/PMID/DOI validators
- Build three indexes: Neo4j (:Concept nodes with vector index), OpenSearch (BM25 + SPLADE rank_features), optional FAISS (dense only)
- Implement catalog build pipeline (download → parse → normalize → enrich/crosswalk → merge → embed → write)
- Add license gating (mark license_bucket; filter query results per caller tier)
- Create cron-based updater service (quarterly/monthly per source)
- Implement ID validators (RxCUI, UNII, NCT, DOI, LOINC, SNOMED, GTIN-14 with checksums)

## Impact

- **Affected specs**: NEW `concept-catalog` capability
- **Affected code**: NEW `/ontology/loaders/`, `/ontology/lexicon/`, concept schemas
- **Dependencies**: Neo4j, OpenSearch, vLLM (embeddings), SPLADE; source downloads (SNOMED requires affiliate license, UMLS requires acceptance, MedDRA requires subscription)
- **Downstream**: Entity linking (candidate generation), retrieval (synonym expansion), extraction (code mapping)
