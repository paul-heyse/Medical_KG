# Quick Reference: Implementation Order & Setup

## 📋 Implementation Order (1-18)

### Phase 1: Foundation & Configuration

1. **add-config-management** - Configuration system (1-2 weeks)
2. **add-data-ingestion-core** - All 17 medical data sources (3-4 weeks)
3. **add-ir-normalization** - Document/Block/Table schemas (2-3 weeks)

### Phase 2: Core Data Infrastructure

4. **add-knowledge-graph** - Neo4j CDKO-Med schema (2-3 weeks)
5. **add-concept-catalog** - 10+ ontologies loaded (3-4 weeks)
6. **add-semantic-chunking** - Medical-aware chunking (2-3 weeks)

### Phase 3: Embeddings & Retrieval

7. **add-embeddings-gpu** - Qwen + SPLADE (2-3 weeks)
8. **add-retrieval-fusion** - BM25/SPLADE/Dense fusion (2-3 weeks)

### Phase 4: PDF Processing (Parallel Track)

9. **add-pdf-mineru-pipeline** - GPU-only PDF (3-4 weeks, parallel with Phase 3)

### Phase 5: Intelligence Layer

10. **add-entity-linking** - NER + LLM adjudication (3-4 weeks)
11. **add-facet-summaries** - Compact summaries (2-3 weeks)
12. **add-clinical-extraction** - PICO/Effects/AEs (4-5 weeks)

### Phase 6: APIs & User Outputs

13. **add-core-apis** - REST APIs (3-4 weeks)
14. **add-briefing-outputs** - Dossiers & evidence maps (3-4 weeks)

### Phase 7: Operations & Production Readiness

15. **add-infrastructure** - K8s, monitoring, orchestration (4-5 weeks)
16. **add-quality-evaluation** - Test harness, CI gates (3-4 weeks)
17. **add-security-compliance** - SHACL, audit, encryption (3-4 weeks)
18. **add-deployment-ops** - Runbooks, E2E tests, DR (2-3 weeks)

**Total Timeline**: ~47-63 weeks sequential (9-12 months with parallelization)

---

## 🚀 Quick Start Commands

### Install Dependencies

```bash
# Using micromamba (recommended)
micromamba install -p ./.venv -c conda-forge python=3.12
micromamba activate ./.venv

# Install project dependencies
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Download spaCy models
python -m spacy download en_core_sci_md
python -m spacy download en_core_web_sm
```

### Environment Setup

```bash
# Copy example env file
cp .env.example .env

# Edit with your API keys
vim .env
```

### Verify Installation

```bash
# Run tests
pytest -q

# Check code quality
ruff check src tests
black --check .
mypy src

# Validate OpenSpec proposals
openspec validate --strict
```

---

## 📦 Key Dependencies by Category

### Core Infrastructure

- `fastapi` - REST APIs
- `neo4j` - Knowledge graph
- `opensearch-py` - Search & retrieval
- `boto3` - Object storage (S3)
- `redis` - Caching

### NLP & ML

- `spacy`, `scispacy` - NER
- `transformers` - SPLADE, tokenization
- `sentence-transformers` - Embeddings
- `torch` - Deep learning

### GPU-Only Processing

- `vllm` - LLM serving (Qwen embeddings, extraction)
- `mineru[all]` - PDF processing

### Data Processing

- `pandas` - Data manipulation
- `httpx` - HTTP client for data sources
- `beautifulsoup4`, `lxml` - HTML/XML parsing

### Observability

- `prometheus-client` - Metrics
- `opentelemetry-*` - Distributed tracing
- `prefect` - Workflow orchestration

### Development

- `pytest` - Testing framework
- `black` - Code formatting
- `ruff` - Linting
- `mypy` - Type checking

---

## 🎯 MVP Timeline (3-4 Months)

For rapid proof-of-concept:

1. Config Management (1 week)
2. Data Ingestion - PMC only (2 weeks)
3. IR Normalization (2 weeks)
4. Knowledge Graph - basic (2 weeks)
5. Semantic Chunking - IMRaD only (2 weeks)
6. Embeddings - Qwen only (2 weeks)
7. Retrieval - BM25 + Dense (2 weeks)
8. Core APIs - minimal (2 weeks)

**MVP Result**: Search medical literature with semantic retrieval

---

## 📈 Scaling Considerations

### GPU Requirements

- **MinerU (Proposal 9)**: 1-2 A100 GPUs
- **Embeddings (Proposal 7)**: 2-4 A100 GPUs (target ≥2.5K tokens/s)
- **Entity Linking (Proposal 10)**: 1 GPU for LLM adjudication
- **Clinical Extraction (Proposal 12)**: 1-2 GPUs for extractors

### Infrastructure Estimates

- **Neo4j**: 32-64 GB RAM, 500GB-1TB SSD
- **OpenSearch**: 3-node cluster, 64GB RAM each
- **Object Store (S3)**: ~5TB for IR + artifacts
- **Redis**: 16-32 GB RAM

---

## 🔍 Critical Paths

### Data Flow

```
Ingest → IR Normalize → Chunk → Embed → Index → Retrieve → Extract → KG Write
```

### Dependencies

- Retrieval needs: Embeddings, Chunking
- Entity Linking needs: Retrieval, Concept Catalog
- Clinical Extraction needs: Entity Linking, Retrieval
- Briefing Outputs needs: Clinical Extraction, KG

---

## ✅ Checklist Before Starting Implementation

- [ ] Read all 18 proposals
- [ ] Obtain stakeholder sign-offs
- [ ] Provision GPU infrastructure
- [ ] Acquire required licenses (SNOMED, UMLS, MedDRA if needed)
- [ ] Set up development environment
- [ ] Install dependencies (`pip install -e ".[dev]"`)
- [ ] Configure API keys in `.env`
- [ ] Run validation (`openspec validate --strict`)
- [ ] Set up git branch (`git checkout -b cx/implement-config-management`)

---

For detailed implementation order with dependencies and timelines, see `IMPLEMENTATION_ORDER.md`.
