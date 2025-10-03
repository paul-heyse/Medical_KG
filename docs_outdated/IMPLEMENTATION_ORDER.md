# Implementation Order for OpenSpec Proposals

This document defines the recommended implementation order for all 18 proposals, considering dependencies, infrastructure needs, and iterative development.

---

## Phase 1: Foundation & Configuration (Proposals 1-3)

### 1. **add-config-management**

**Why First**: Configuration system needed by all other components. Hot-reload, secrets management, and environment-specific configs are foundational.

- Dependencies: None
- Outputs: config.yaml, policy.yaml, validation, hot-reload
- Duration: 1-2 weeks

### 2. **add-data-ingestion-core**

**Why Second**: Need data flowing before processing. All 17 medical sources with HTTP client, ledger, validation.

- Dependencies: Config management
- Outputs: Ingestion for PubMed, PMC, ClinicalTrials, DailyMed, RxNorm, etc.
- Duration: 3-4 weeks

### 3. **add-ir-normalization**

**Why Third**: Normalizes ingested data to consistent structure. Required before any processing.

- Dependencies: Data ingestion
- Outputs: Document/Block/Table schemas, canonicalization, validation
- Duration: 2-3 weeks

---

## Phase 2: Core Data Infrastructure (Proposals 4-6)

### 4. **add-knowledge-graph**

**Why Fourth**: Central data store needed before chunking can write data. Neo4j schema, constraints, indexes.

- Dependencies: IR normalization, config management
- Outputs: CDKO-Med schema, vector indexes, SHACL validation setup
- Duration: 2-3 weeks

### 5. **add-concept-catalog**

**Why Fifth**: Ontologies needed for entity linking and extraction. Can load while other work progresses.

- Dependencies: Knowledge graph (for storage), config (for licensing)
- Outputs: SNOMED, ICD-11, LOINC, RxNorm, MeSH, UMLS, etc. loaded
- Duration: 3-4 weeks

### 6. **add-semantic-chunking**

**Why Sixth**: Chunks documents for downstream processing. Writes to KG.

- Dependencies: IR normalization, knowledge graph
- Outputs: Medical-aware chunking, coherence-based boundaries, facet routing
- Duration: 2-3 weeks

---

## Phase 3: Embeddings & Retrieval (Proposals 7-8)

### 7. **add-embeddings-gpu**

**Why Seventh**: Compute embeddings for chunks and concepts. Required for retrieval.

- Dependencies: Semantic chunking (chunks), concept catalog (concepts)
- Outputs: vLLM Qwen embeddings, SPLADE expansion, GPU enforcement
- Duration: 2-3 weeks

### 8. **add-retrieval-fusion**

**Why Eighth**: Enable search over embedded chunks. Foundation for extraction and briefing.

- Dependencies: Embeddings (dense/sparse vectors), chunking (indexed chunks)
- Outputs: BM25/SPLADE/Dense fusion, intent routing, reranking
- Duration: 2-3 weeks

---

## Phase 4: PDF Processing (Parallel Track - Proposal 9)

### 9. **add-pdf-mineru-pipeline**

**Why Parallel**: Can run alongside Phase 3-4. GPU-only PDF processing with manual gates.

- Dependencies: Config, data ingestion (PDF download), IR normalization (output format)
- Outputs: MinerU runner, QA gates, medical post-processing
- Duration: 3-4 weeks
- **Note**: Run in parallel with embeddings/retrieval work

---

## Phase 5: Intelligence Layer (Proposals 10-12)

### 10. **add-entity-linking**

**Why Tenth**: Links entities to concepts. Needs retrieval for candidate generation.

- Dependencies: Retrieval (candidate generation), concept catalog (concepts), chunking (chunks)
- Outputs: NER stack, candidate generation, LLM adjudication, review queue
- Duration: 3-4 weeks

### 11. **add-facet-summaries**

**Why Eleventh**: Compact summaries for chunks. Can generate after chunking but benefits from having EL.

- Dependencies: Chunking (chunks), embeddings (optional facet embeddings)
- Outputs: PICO/endpoint/AE/dose facets, token budget enforcement, deduplication
- Duration: 2-3 weeks

### 12. **add-clinical-extraction**

**Why Twelfth**: Extracts structured clinical data. Needs entity linking for code resolution.

- Dependencies: Entity linking (code resolution), retrieval (chunk selection), facets (routing)
- Outputs: PICO, Effects, AEs, Dose, Eligibility extractors with span grounding
- Duration: 4-5 weeks

---

## Phase 6: APIs & User Outputs (Proposals 13-14)

### 13. **add-core-apis**

**Why Thirteenth**: Expose all functionality via REST APIs. Needs most capabilities implemented.

- Dependencies: All data processing capabilities (1-12)
- Outputs: OpenAPI 3.1 spec, all endpoints, auth, rate limiting, licensing filters
- Duration: 3-4 weeks

### 14. **add-briefing-outputs**

**Why Fourteenth**: Generate user-facing dossiers and evidence maps. Needs extraction and KG.

- Dependencies: Clinical extraction, entity linking, knowledge graph, retrieval
- Outputs: Topic dossiers, evidence maps, interview kits, Q&A mode
- Duration: 3-4 weeks

---

## Phase 7: Operations & Production Readiness (Proposals 15-18)

### 15. **add-infrastructure**

**Why Fifteenth**: K8s, orchestration, monitoring. Implement as capabilities are built.

- Dependencies: All services (1-14) to deploy
- Outputs: K8s manifests, Helm charts, DAGs, Prometheus, Grafana, Terraform
- Duration: 4-5 weeks
- **Note**: Start K8s basics early, add monitoring/orchestration as services are ready

### 16. **add-quality-evaluation**

**Why Sixteenth**: Formalize evaluation harness. Create gold sets and run evals.

- Dependencies: All capabilities to evaluate (chunking through briefing)
- Outputs: Gold sets, query sets, eval scripts, CI gates, drift detection
- Duration: 3-4 weeks

### 17. **add-security-compliance**

**Why Seventeenth**: SHACL validation, licensing enforcement, audit logging, encryption.

- Dependencies: Knowledge graph (SHACL), APIs (licensing filters), all writes (audit)
- Outputs: SHACL shapes, licensing enforcement, audit logs, encryption, RBAC
- Duration: 3-4 weeks
- **Note**: Some aspects (licensing) implemented earlier, formalized here

### 18. **add-deployment-ops**

**Why Last**: Final production readiness. Runbooks, E2E tests, release checklist.

- Dependencies: All capabilities (1-17)
- Outputs: Runbooks, E2E verification, load testing, chaos testing, release checklist
- Duration: 2-3 weeks

---

## Summary Timeline

### Sequential Phases (Minimum)

- **Phase 1**: 6-9 weeks (Config + Ingestion + IR)
- **Phase 2**: 7-10 weeks (KG + Catalog + Chunking)
- **Phase 3**: 4-6 weeks (Embeddings + Retrieval)
- **Phase 4**: 3-4 weeks (PDF - parallel)
- **Phase 5**: 9-12 weeks (EL + Facets + Extraction)
- **Phase 6**: 6-8 weeks (APIs + Briefing)
- **Phase 7**: 12-14 weeks (Infra + Eval + Security + Ops)

**Total Sequential**: ~47-63 weeks (11-15 months)

### With Parallelization

- PDF processing (Phase 4) runs parallel with Phase 3
- Infrastructure work (Phase 7.15) starts early and runs continuously
- Some security aspects (licensing) implemented earlier

**Realistic with 3-4 engineers**: ~9-12 months to production-ready

---

## Critical Path

```
Config → Data Ingestion → IR Normalization → Knowledge Graph → Semantic Chunking → Embeddings → Retrieval → Entity Linking → Clinical Extraction → Core APIs → Briefing Outputs → Full Production Readiness
```

## Parallel Tracks

- **PDF Track**: Can start after Config/Ingestion (parallel with embeddings/retrieval)
- **Infrastructure Track**: Start K8s basics early, add services as implemented
- **Evaluation Track**: Create gold sets early, run evals as capabilities complete
- **Security Track**: Implement licensing early, formalize audit/encryption later

---

## Quick Start (MVP - First 3-4 Months)

For a minimal viable product to demonstrate value:

1. Config Management (1 week)
2. Data Ingestion - PMC only (2 weeks)
3. IR Normalization (2 weeks)
4. Knowledge Graph - basic schema (2 weeks)
5. Semantic Chunking - IMRaD only (2 weeks)
6. Embeddings - Qwen only (2 weeks)
7. Retrieval - BM25 + Dense only (2 weeks)
8. Core APIs - minimal endpoints (2 weeks)

**MVP Timeline**: ~3-4 months with 2-3 engineers

---

## Notes

- **GPU Requirements**: Proposals 9 (MinerU), 7 (Embeddings), 10 (Entity Linking LLM), 12 (Clinical Extraction LLM) all require GPU
- **Data Dependencies**: Proposals 2→3→4→6→7→8 form critical path for data flow
- **Approval Gates**: Each proposal requires stakeholder sign-off before implementation starts
- **Iterative Development**: Start simple (fewer sources, simpler models) and add complexity incrementally
