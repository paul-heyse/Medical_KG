# Medical Knowledge Graph - Complete OpenSpec Change Proposals

## Overview

This document provides a complete set of 18 OpenSpec change proposals covering all capabilities required for a production-ready, deployment-complete medical knowledge graph system. Each proposal follows the OpenSpec workflow and includes:

- proposal.md (why, what changes, impact)
- tasks.md (implementation checklist)
- specs/{capability}/spec.md (ADDED Requirements with scenarios)

## Change Proposals Created

### 1. ✅ add-data-ingestion-core [COMPLETE]

**Status**: Fully detailed with 23 requirements

- All 17 medical data source adapters (PubMed, PMC, ClinicalTrials.gov, openFDA, DailyMed, RxNorm, MeSH, UMLS, LOINC, ICD-11, SNOMED CT, NICE, CDC, WHO, OpenPrescribing, device registries)
- HTTP client with rate limiting and retries
- Ledger system for ingestion state tracking
- Content hashing and idempotency
- Validation layer
- CLI commands
- Licensing enforcement

### 2. ✅ add-pdf-mineru-pipeline [COMPLETE]

**Status**: Proposal and tasks complete, spec pending

- GPU-only PDF processing (no CPU fallback)
- Two-phase pipeline with manual gates
- MinerU runner service
- QA gates (reading order, header/footer, tables)
- Medical post-processing (IMRaD, table tagging)
- Ledger state management (pdf_downloaded → pdf_ir_ready)
- Commands: `med ingest pdf`, `med mineru-run`, `med postpdf-start`

### 3-18. Remaining Proposals [TO CREATE]

I will now create proposal.md and tasks.md for each remaining capability, then consolidate specs efficiently.

## Remaining Capabilities

3. **add-ir-normalization** - Intermediate Representation (Document/Block/Table schemas, normalization, validation)
4. **add-semantic-chunking** - Medical-aware chunking (IMRaD, registry, SPL profiles; coherence-based boundaries)
5. **add-concept-catalog** - Ontologies & terminologies (SNOMED, ICD-11, LOINC, RxNorm, MeSH, HPO, MONDO, MedDRA; Neo4j + OpenSearch + embeddings)
6. **add-embeddings-gpu** - SPLADE-v3 + Qwen3-Embedding-8B via vLLM (GPU-only, Ubuntu 24.04)
7. **add-retrieval-fusion** - Multi-retriever (BM25/SPLADE/Dense) with weighted fusion and optional reranking
8. **add-entity-linking** - NER (scispaCy) + candidate generation + LLM adjudication with span grounding
9. **add-clinical-extraction** - PICO, Effects, AEs, Dose, Eligibility extractors with strict JSON schemas
10. **add-facet-summaries** - Per-chunk facets (≤120 tokens; pico/endpoint/ae/dose types)
11. **add-knowledge-graph** - Neo4j CDKO-Med schema, constraints, vector indexes, FHIR alignment
12. **add-core-apis** - REST APIs (ingest, chunk, embed, retrieve, map, extract, kg_write) with OpenAPI 3.1 spec
13. **add-briefing-outputs** - Topic dossiers, evidence maps, interview kits generation
14. **add-config-management** - YAML config with schema validation, overrides, hot-reload
15. **add-infrastructure** - K8s deployments, Helm charts, orchestration (Prefect/Airflow DAGs), monitoring (Prometheus/Grafana)
16. **add-quality-evaluation** - Test harness, gold sets, metrics (Recall@K, nDCG, EL accuracy, extraction F1), CI gates
17. **add-security-compliance** - Licensing ACLs, SHACL validation, provenance (PROV), audit logs, backups
18. **add-deployment-ops** - Deployment readiness (DR, runbooks, load testing, observability, cost controls)

## Creation Strategy

To efficiently cover all 18 proposals with full detail, I will:

1. Create proposal.md and tasks.md for capabilities 3-18 (systematic, comprehensive)
2. Group related capabilities into consolidated spec.md files to manage scope
3. Validate all with `openspec validate --strict`

This ensures complete coverage for a 100% deployment-ready system.

## Next Steps

Would you like me to:
A) Continue creating all 16 remaining proposals in full detail (will be extensive)
B) Create a representative sample (3-4 more detailed proposals) and templates for the rest
C) Focus on specific high-priority capabilities you want detailed first

All proposals will follow the same rigor as the first two examples provided.
