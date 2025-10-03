# Medical Knowledge Graph - OpenSpec Change Proposals Status

## Executive Summary

Creating 18 comprehensive OpenSpec change proposals covering all capabilities for a **100% deployment-ready** medical knowledge graph system. Each proposal includes proposal.md, tasks.md, and will include detailed spec.md files with ADDED Requirements and Scenarios.

## Completed Proposals (7/18) - Fully Detailed

### ✅ 1. add-data-ingestion-core

- **Files**: proposal.md ✓, tasks.md ✓, specs/data-ingestion/spec.md ✓ (23 requirements)
- **Scope**: All 17 medical data sources, HTTP client, ledger, validation, CLI, licensing
- **Lines of spec**: ~850 lines with detailed scenarios

### ✅ 2. add-pdf-mineru-pipeline

- **Files**: proposal.md ✓, tasks.md ✓, spec.md pending
- **Scope**: GPU-only PDF processing, two-phase pipeline, QA gates, MinerU runner

### ✅ 3. add-ir-normalization

- **Files**: proposal.md ✓, tasks.md ✓, spec.md pending
- **Scope**: Document/Block/Table schemas, canonicalization, span mapping, validation

### ✅ 4. add-semantic-chunking

- **Files**: proposal.md ✓, tasks.md ✓, spec.md pending
- **Scope**: Domain profiles, clinical tagger, coherence-based chunking, facet generation

### ✅ 5. add-concept-catalog

- **Files**: proposal.md ✓, tasks.md ✓, spec.md pending
- **Scope**: All ontologies (SNOMED, ICD-11, LOINC, RxNorm, MeSH, HPO, MONDO, MedDRA), loaders, embeddings, license gating

### ✅ 6. add-embeddings-gpu

- **Files**: proposal.md ✓, tasks.md ✓, spec.md pending
- **Scope**: vLLM + Qwen3-Embedding-8B, SPLADE-v3, GPU enforcement, batch processing

### ✅ 7. add-knowledge-graph

- **Files**: proposal.md ✓, tasks.md ✓, spec.md pending
- **Scope**: Neo4j CDKO-Med schema, constraints, FHIR exporters, SHACL validation

## Remaining Proposals (11/18) - To Create

### 8. add-retrieval-fusion

- **Scope**: BM25/SPLADE/Dense multi-retriever, weighted fusion, RRF, optional reranking, intent routing, neighbor-merge
- **Status**: Creating now

### 9. add-entity-linking

- **Scope**: NER (scispaCy), QuickUMLS, candidate generation, LLM adjudication, span grounding
- **Status**: To create

### 10. add-clinical-extraction

- **Scope**: PICO, Effects, AEs, Dose, Eligibility extractors with strict JSON schemas, LLM prompts, normalizers
- **Status**: To create

### 11. add-facet-summaries

- **Scope**: Per-chunk facet generation (≤120 tokens; pico/endpoint/ae/dose types), routing, validation
- **Status**: To create

### 12. add-core-apis

- **Scope**: REST APIs (ingest, chunk, embed, retrieve, map, extract, kg_write), OpenAPI 3.1 spec, auth, idempotency
- **Status**: To create

### 13. add-briefing-outputs

- **Scope**: Topic dossiers, evidence maps, interview kits generation from KG queries
- **Status**: To create

### 14. add-config-management

- **Scope**: YAML config with schema, overrides, hot-reload, validation
- **Status**: To create

### 15. add-infrastructure

- **Scope**: K8s deployments, Helm charts, Prefect/Airflow DAGs, monitoring (Prometheus/Grafana)
- **Status**: To create

### 16. add-quality-evaluation

- **Scope**: Test harness, gold sets, metrics (Recall@K, nDCG, EL accuracy, extraction F1), CI gates
- **Status**: To create

### 17. add-security-compliance

- **Scope**: Licensing ACLs, SHACL validation, provenance (PROV), audit logs, backups, DR
- **Status**: To create

### 18. add-deployment-ops

- **Scope**: Deployment readiness, runbooks, load testing, observability, cost controls, final E2E verification
- **Status**: To create

## Strategy for Completion

Given the comprehensive scope, I will:

1. Continue creating proposal.md and tasks.md for proposals 8-18 (systematic, detailed)
2. Create consolidated spec.md files grouping related capabilities to manage scope efficiently
3. Ensure all proposals include:
   - Clear "Why" (problem statement)
   - Detailed "What Changes" (features and components)
   - Complete "Impact" (affected code, dependencies, downstream)
   - Exhaustive task lists (10-12 sections each with subtasks)
   - Comprehensive specs with ADDED Requirements and Scenarios (following OpenSpec format)
4. Validate all with `openspec validate --strict` before marking complete

## Next Actions

Continuing to create remaining 11 proposals now...
