# Mercor Project Descriptor (Medicine): Pre‑Engagement Knowledge Readiness

## 1) Context & Purpose

**Mercor’s work process** begins with *deep domain familiarization before engaging participants*. This project builds a **medical knowledge readiness engine** that compiles high‑value research and reference material into an **organized, queryable structure** so the team can surface all relevant facts, controversies, and evidence **before interviews, workshops, or solution design**.

In short: **ingest medical literature and structured sources → normalize and structure → extract key facts with provenance → organize into a graph and searchable index → produce briefing‑quality outputs for targeted topics.**

---

## 2) Objectives

* **Pre‑engagement mastery:** Equip Mercor analysts with comprehensive, evidence‑backed understanding of any medical topic (e.g., a therapy area, device class, biomarker strategy) prior to conversations with participants.
* **Structured evidence base:** Transform disparate sources (trials, journals, labels, guidelines) into a **coherent, navigable knowledge graph** aligned to clinical ontologies and standards.
* **Targeted retrieval:** Enable precise, intent‑aware search (PICO, endpoints, dose, eligibility, adverse events, recommendations) with **span‑grounded citations**.
* **Briefing assets:** Auto‑assemble **topic dossiers, evidence maps, and interview question banks** customized to the engagement.

---

## 3) Scope (v1: Medicine only)

**In scope**

* Sources: ClinicalTrials.gov (v2), PubMed/PMC (OA subset), DailyMed SPL, device registries (GUDID/openFDA), major guidelines (HTML/PDF).
* Structured standards/ontologies: FHIR Evidence/EvidenceVariable alignment; SNOMED CT, ICD‑11, LOINC (+ UCUM), RxNorm/UNII, HPO, MONDO, MeSH; MedDRA/CTCAE for AEs.
* Data flow: ingestion → normalization → semantic chunking → embeddings & sparse indexing → ontology‑aware extraction → Neo4j knowledge graph → briefing outputs.
* **GPU‑only** operation for PDF parsing (MinerU), embeddings (Qwen3 via vLLM), and SPLADE‑v3 expansions.

**Out of scope (now)**

* Non‑medical domains (finance, law) — slated for follow‑on phases.
* PHI/EHR ingestion (future; brings privacy controls and de‑ID).
* Image‑only understanding beyond table/caption handling.

---

## 4) Users & Primary Outcomes

**Users**

* Mercor analysts, engagement leads, strategist/PMs, and internal AI agents.

**Outcomes**

* **Topic dossiers** (e.g., “SGLT2 inhibitors in HFrEF”): PICO summary, endpoints and effect sizes, safety signals, dose, guideline stance, key trials, open questions.
* **Evidence maps**: who found what, in which population, with which certainty; linked back to exact source spans.
* **Interview kits**: question bank grounded in gaps, conflicts, and decision points.
* **Live Q&A**: fast, intent‑aware retrieval with citations suitable for meetings.

---

## 5) Value Proposition

* **Speed:** Days of manual reading condensed into hours of guided review.
* **Coverage:** Multiple source types unified; fewer blind spots during interviews.
* **Confidence:** Every claim links to **verbatim spans** (page/offset) and source metadata.
* **Re‑use:** Knowledge persists in a graph; new sources enrich existing topics.

---

## 6) High‑Level Approach

1. **Ingestion & Source Adapters**

   * ClinicalTrials.gov (v2 JSON), PMC JATS XML / PubMed abstracts, DailyMed SPL XML, device registries (JSON), guidelines (HTML/PDF).
   * **PDFs follow a two‑phase path**: download → **manual/dedicated GPU step with MinerU** → IR; **no automatic transition**.

2. **Normalization to IR (Intermediate Representation)**

   * Uniform JSONL with `Document`, `Block`, and `Table` objects; preserves structure, offsets, page/bbox for precise provenance.

3. **Semantic Chunking (Medical‑aware)**

   * Chunks respect clinical boundaries (IMRaD sections, outcome measures, eligibility inclusion/exclusion, SPL LOINC sections).
   * Per‑chunk **facet summaries** (PICO, endpoint, AE, dose, eligibility, recommendation).

4. **Indexing & Retrieval**

   * **Dense embeddings**: Qwen3‑Embedding‑8B served via **vLLM** (GPU).
   * **Sparse signals**: BM25/BM25F and **SPLADE‑v3** (GPU doc expansion).
   * **Fusion** of sparse+dense for high recall, plus optional rerank.

5. **Ontology‑Aware Extraction & Mapping**

   * Entity linking to clinical ontologies; extraction of PICO, effects (HR/RR/OR/CI/p), AEs (MedDRA + CTCAE grade), dose (UCUM), eligibility logic (LOINC + thresholds).
   * All assertions carry **char offsets + verbatim quotes** and PROV metadata.

6. **Knowledge Graph (Neo4j)**

   * Medical pseudo‑ontology (CDKO‑Med) aligned with FHIR; nodes for Studies, Arms, Interventions (Drug/Device), Conditions/Phenotypes, Outcomes, Evidence, Eligibility, AEs, Identifiers.
   * Constraints & SHACL validation for codes/units/IDs.

7. **Briefing & Delivery**

   * Topic dossiers, evidence maps, interview kits, and queryable dashboards, all backed by citations.

---

## 7) Processing Sequence & GPU Policy (Key Operating Model)

* **Non‑PDF sources**: run the **auto pipeline** end‑to‑end (download → IR → chunk → embed → index → map/extract → KG).
* **PDF sources**:

  * **Stop after download** (ledger `pdf_downloaded`).
  * Manually or via GPU queue, run **`mineru-run`** (GPU‑only) → IR (ledger `pdf_ir_ready`).
  * Only then explicitly run **`postpdf-start`** to continue downstream stages.
* **GPU enforcement (Ubuntu 24.04)**: MinerU, Qwen embeddings (vLLM), and SPLADE expansions **must detect CUDA**; **no CPU fallback** (jobs fail fast with clear diagnostics).

---

## 8) Data & Ontology Strategy (Medical)

* **Identifiers:** NCT, PMID/PMCID/DOI, RxCUI/UNII, UDI‑DI, LOINC codes, UCUM units, ICD‑11, SNOMED CT, MedDRA/CTCAE, HPO, MONDO, MeSH.
* **Standards:** FHIR Evidence/EvidenceVariable compatibility; OMOP cross‑walk (optional).
* **Concept Lexicon:** labels + synonyms + definitions with embeddings; used for high‑recall candidate generation and ontology‑aware queries.

---

## 9) Key Deliverables

* **Knowledge Graph** (Neo4j) with clinical nodes/edges + constraints and provenance.
* **Search stack** with BM25/SPLADE/Qwen fusion and clinical **facet retrieval**.
* **Topic dossiers & interview kits**, parameterized by therapeutic area/device/problem statement.
* **Admin & QA dashboards** for coverage, drift, and extraction quality.
* **Runbooks** (GPU setup, MinerU operations, vLLM serving, rebuilds).

---

## 10) Quality, Compliance, and Governance

* **Evidence fidelity:** 100% of asserted facts carry `doc_id`, `start/end` offsets, and quotes.
* **Validation:** SHACL for IDs/units/codes; checksum rules for identifiers; UCUM normalization.
* **Licensing:** SNOMED CT (affiliate), UMLS (acceptance), MedDRA (subscription), open vocabularies (attribution). Loaders respect licenses via config flags.
* **Security:** Service‑to‑service mTLS, Vault‑managed secrets, network isolation for data stores.
* **Auditability:** PROV on every extraction; content and IR hashing; MinerU run IDs.

---

## 11) Roles & Responsibilities

* **Domain Lead (Clinical):** defines topics, validates extractions, approves dossiers.
* **Data/ML Engineer:** adapters, IR builder, chunker, embeddings/indexing, GPU operations (vLLM, SPLADE, MinerU).
* **Ontology/Graph Engineer:** ontology loaders, KG schema, SHACL, mapping logic.
* **Analyst / Engagement Lead:** configures topics, reviews outputs, compiles interview kits.
* **Ops:** monitors pipelines, GPUs, indexes, and graph health.

---

## 12) Success Criteria (Definition of Ready for Engagement)

* For any defined topic, the system can produce within one run:

  * **PICO synopsis**, **endpoint effect sheet** (values + CI + p), **safety profile** (AEs with MedDRA + grade), **dose guidance** (UCUM), **eligibility snapshot**, and **guideline stance**, **all with citations**.
  * **Coverage report** listing included studies, labels, guidelines, and known gaps.
  * **Interview kit** autogenerated from gaps and decision points.
* Retrieval meets **intent‑level recall and nDCG** targets on internal benchmarks.
* No GPU fallbacks occurred; all extractions pass validation thresholds.

---

## 13) Illustrative User Stories

* **Analyst:** “Given ‘GLP‑1 RAs for obesity’, generate a dossier with top trials, endpoints (weight change, CV outcomes), key AEs (GI, gallbladder), dosing/titration, guideline recommendations, and eligibility patterns.”
* **Engagement Lead:** “Before expert interviews, auto‑propose questions on unresolved evidence (e.g., long‑term safety, subpopulation effects) with source links.”
* **Engineer:** “Ingest the latest guideline PDF; run MinerU on GPU; update the KG and regenerate the dossier automatically.”

---

## 14) Dependencies & Assumptions

* Reliable access to source APIs and OA content; adherence to licensing.
* Availability of **CUDA‑enabled GPUs** and **vLLM** service for embeddings.
* MinerU container available; object store for artifacts and IR.
* Neo4j with APOC + n10s, and search/vector infra (ES/OpenSearch + FAISS or equivalent).

---

## 15) Risks & Mitigations (selected)

* **Licensing constraints** (SNOMED/UMLS/MedDRA) → loader flags, ACLs, audit logs.
* **GPU contention** → dedicated queues for MinerU/embeddings, capacity planning.
* **PDF variability** → MinerU QA gates, manual review queue, sliding‑window fallback for retrieval.
* **Extraction drift** → nightly evals; thresholds & selective prediction; human review on low‑confidence.

---

## 16) What “Good” Looks Like at Handover

* A **repeatable pipeline** that, for a new clinical topic, delivers:

  * A **navigable knowledge graph**,
  * A **searchable workspace** with clinical facets, and
  * A **briefing pack** (dossier + interview kit) — all **evidence‑linked** and **licensing‑compliant**.

This descriptor is intended as the **single source of truth** for the project’s purpose, scope, operating model, and success definition in Mercor’s pre‑engagement process.

Below is the **fully integrated, medicine‑only specification for Sections 1–4**, merging the earlier highly detailed content with your added requirements:

* **PDFs are processed by MinerU in a separate, manual GPU‑only step** (no automatic transition to chunking/embedding).
* **All non‑PDF sources run the full pipeline automatically.**
* **GPU is mandatory** for MinerU, SPLADE‑v3 doc expansion, and Qwen3‑Embedding‑8B via **vLLM** on **Ubuntu 24.04**. There is **no CPU fallback** anywhere in the flow.

I’ve kept **all** earlier details and added the exact **control flow, commands, GPU enforcement, and vLLM specifics** so agents can implement it directly.

---

# 1) SOURCES & ADAPTERS (MEDICINE) — WITH PDF/VLLM/GPU INTEGRATION

## 1.0 Ingestion modes & control flow (authoritative)

Two execution modes are supported; choice depends on **media_type**:

**A) Auto‑pipeline (non‑PDF)**

```
download → parse → IR → chunk → facet → embed (SPLADE+Qwen via vLLM, GPU) → index → (optional) extract/map → KG
```

Applies to: **ClinicalTrials.gov v2 JSON**, **PMC/JATS XML**, **DailyMed SPL XML**, **GUDID/openFDA UDI JSON**, most **HTML guidelines**.

**B) Two‑phase pipeline (PDFs)**

```
download → (STOP) → mineru-run (GPU) → IR → (STOP) → postpdf-start → chunk → facet → embed (GPU) → index → (optional) extract/map → KG
```

* MinerU is **never chained** automatically into chunking/embedding.
* **You (or a GPU queue) must explicitly run `mineru-run`** and **then** explicitly run `postpdf-start` for downstream steps.

**Ledger states** (single source of truth for orchestration):

* `pdf_downloaded` → raw PDF landed (no further action taken)
* `pdf_ir_ready` → MinerU artifacts converted & IR produced (awaiting `postpdf-start`)
* `auto_inflight` / `auto_done` → non‑PDF auto pipeline status markers
* Failure states: `mineru_failed`, `embed_failed`, etc., with error payloads

---

## 1.1 Overview table (unchanged content, now with flow flags)

| Source                       | Why                                    | Preferred input           | Alternate input                         | Identifiers extracted                                                        | Outputs (IR types)                     | Flow                                  |
| ---------------------------- | -------------------------------------- | ------------------------- | --------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------- |
| ClinicalTrials.gov (CTG)     | Canonical registry of clinical studies | **v2 JSON**               | HTML (fallback)                         | `NCT`, orgs, locations, conditions, interventions, outcome measures, results | `Document`, `Block`, `Table`           | **Auto**                              |
| PubMed / PMC (OA)            | Peer‑reviewed literature               | **JATS/NXML**             | Abstract (Medline JSON), **PDF→MinerU** | `PMID`, `PMCID`, `DOI`, ORCIDs, MeSH                                         | `Document`, `Block`, `Table`, captions | **Auto** (JATS) / **Two‑phase** (PDF) |
| DailyMed SPL                 | Structured drug labels                 | **SPL XML (LOINC‑coded)** | PDF→MinerU                              | `SPL setid`, `NDC`, `RxCUI` (derived), `UNII`                                | `Document`, `Block`, `Table`           | **Auto** (XML) / **Two‑phase** (PDF)  |
| Devices: GUDID / openFDA UDI | Device metadata & UDI                  | **JSON APIs**             | HTML                                    | `UDI‑DI`, brand, GMDN                                                        | `Document`, `Block`                    | **Auto**                              |
| Guidelines                   | Practice recommendations               | **HTML**                  | **PDF→MinerU**                          | publisher IDs, recommendation IDs, GRADE                                     | `Document`, `Block`, `Table`           | **Auto** (HTML) / **Two‑phase** (PDF) |

---

## 1.2 Adapter contracts (I/O; flow control additions)

Every adapter implements:

* `fetch(source_id|query) -> RawBundle` (bytes + metadata)
* `parse(raw) -> IR JSONL` (emits `Document`, `Block`, `Table`)
* `validate(ir) -> ValidationReport` (schema + semantics)
* `write(ir) -> object_store_uri` (idempotent)

**Flow control rules**

* **PDF adapters** (PMC PDFs, guideline PDFs, SPL PDFs):

  * Stop after `fetch()`. Persist the raw PDF and insert a ledger record `{doc_key, media_type:'pdf', status:'pdf_downloaded'}`. **Do not** call `parse()` here.
* **MinerU runner** (separate script/service, GPU‑only):

  * Consumes ledger items with `status='pdf_downloaded'`, produces MinerU artifacts (Markdown, Blocks JSON, Tables HTML + offset map), builds IR JSONL, then sets `status='pdf_ir_ready'`.
* **Post‑MinerU trigger**:

  * `postpdf-start` consumes `status='pdf_ir_ready'` and runs `IR → chunk → facet → embed → index` (and optional extract/map → KG). **No auto transition**.

**CLI / API commands**

```bash
# Download PDF only (no auto processing)
med ingest pdf --uri <https|s3> --doc-key <DOC_KEY>

# MinerU (GPU-only) – manual / queued
med mineru-run --from-ledger --filter status=pdf_downloaded \
  --in-bucket s3://bucket/raw --out-bucket s3://bucket/mineru \
  --gpus all --fail-if-no-gpu

# Gate into post-MinerU operations (GPU required for embeddings)
med postpdf-start --from-ledger --filter status=pdf_ir_ready \
  --steps ir->chunk->facet->embed->index \
  --gpus all --fail-if-no-gpu

# Non-PDF full auto
med ingest ctgov --nct NCT01234567 --auto
med ingest pmc  --pmcid PMC12345      --auto
med ingest spl  --setid <GUID>        --auto
```

---

## 1.3 GPU enforcement (global; Ubuntu 24.04)

* **REQUIRE_GPU=1** environment flag is honored by all GPU stages (MinerU runner, SPLADE v3 doc expansion, vLLM embeddings).
* Bootstrap checks (fail‑fast; exit code **99**):

  * `nvidia-smi` succeeds & reports ≥ 1 CUDA GPU.
  * For PyTorch‑based stages (SPLADE): `torch.cuda.is_available()` is **true**.
  * For vLLM: server must start with GPU (e.g., `--tensor-parallel-size ≥ 1`) and be reachable.
* **No CPU fallback** is allowed. If checks fail, job aborts and ledger status remains unchanged.
* **Ubuntu 24.04** prerequisites:

  * NVIDIA driver & CUDA installed
  * NVIDIA Container Toolkit installed (for Docker `--gpus all`)

---

## 1.4 ClinicalTrials.gov (registry) — adapter spec (unchanged content)

**Pull**: by NCT (`get_by_nct`) or search/delta (`search({...})`).
**Versioning**: persist `record_version` in `Document.meta` and incorporate into `doc_id`.
**Field normalization** (→ `Document.meta`, `Block`, `Table`): study metadata; conditions; interventions (type, description, candidate codes like RxCUI/UNII/UDI); arms; outcome measures (name, type, unit/scale, time_frame); results (values, CI, p, per arm); participant flow; AEs (term, frequency, seriousness, grade, relatedness); limitations.
**Eligibility**: split Inclusion/Exclusion; bullets → `Block(block_type="eligibility", meta.kind=...)`; parallel **logic** normalization (age ranges; lab thresholds via **LOINC+UCUM**; conditions via MONDO/SNOMED).
**IR emission**: `Document`, structured `Block`s by section, `Table`s for AEs/outcomes/flow.
**Chunking guidance**: treat each Outcome Measure, Results, and Eligibility as separate chunk families; AEs as atomic table chunks.
**Quality checks**: required meta present; numeric sanity; UCUM unit normalization; x‑link integrity.

---

## 1.5 PubMed / PMC — adapter spec (unchanged content + PDF path)

**PMC OA (preferred)**: fetch **JATS/NXML** by `pmcid`.
**PubMed**: abstract/Medline JSON by `pmid`; join to PMC if `pmcid` exists.
**Tables**: parse `table-wrap` to normalized rectangular `rows[]` + keep HTML.
**Figures**: captions as `Block(type="caption")`; store image URI.
**References**: keep numbered citations with `xref` anchors.
**IR emission**: `Document`, `Block` per section/paragraph, `Table` per `table-wrap`.
**Clinical annotations** (optional pre‑pass): PICO span hints; numeric effect candidates.
**Quality checks**: Abstract presence; at least Methods or Results; table integrity.

**PDF articles**: follow **Two‑phase** mode (Section 3). The PMC PDF is downloaded → ledger `pdf_downloaded`. You must run `mineru-run` (GPU) to produce MinerU artifacts and IR → ledger `pdf_ir_ready` → run `postpdf-start` to continue.

---

## 1.6 DailyMed SPL (drug labels) — adapter spec (unchanged content + PDF path)

**Ingestion**: SPL XML by `setid/NDC`; track **version** (store in `Document.meta`).
**LOINC‑coded sections**: Indications, Dosage, Contraindications, Warnings, Adverse Reactions, etc.; attach `meta.loinc_section` to all blocks from that section.
**Ingredients**: active/inactive; map actives to **UNII** and **RxCUI**; keep strengths `{amount, unit, per_unit}`; normalize units via **UCUM** (retain original too).
**AEs**: frequency tables; later map to **MedDRA PT**.
**IR emission**: `Document`, `Block` per section, `Table` for AE/dose.
**Quality**: ensure key sections present; dosage units consistent.

**SPL PDFs**: use **Two‑phase** PDF path via MinerU.

---

## 1.7 Device registries (GUDID / openFDA UDI) — adapter spec (unchanged content)

**Ingestion**: query by **UDI‑DI**; pull attributes (brand, model, labeler, MRI safety, kit, single‑use, sterilization, implantable, life‑support, size/weight, GMDN).
**IR emission**: `Document` with `meta.udi_di`; `Block` per attribute category.
**Quality**: DI format/length; cross‑reference brand vs company.

---

## 1.8 Guidelines — adapter spec (unchanged content + PDF path)

**Ingestion**: prefer HTML; extract **recommendation units** (statement, population/scope, **strength**, **certainty/GRADE**, key citations).
**IR emission**: `Document` guideline; `Block` per recommendation; `Table` for evidence profiles.
**Quality**: atomicity of recommendations; strength/certainty captured.

**Guideline PDFs**: follow **Two‑phase** MinerU path.

---

## 1.9 Adapter engineering details (common; unchanged)

* HTTP retries with exponential backoff + jitter; connect/read timeouts.
* Content hashing: `doc_hash = sha256(canonical_bytes)`; `doc_id = {source}:{id}#{version_or_date}:{hash12}`.
* Normalization (pre‑IR): UTF‑8; Unicode NFKC; whitespace collapse; **de‑hyphenate** only when dictionary confirms; keep **raw_text**.
* Language detection: fasttext/CLD; set `language`.
* Idempotency: if `doc_id` exists, skip; if same hash within batch, skip.

---

## 1.10 GPU services & prerequisites (new)

* **vLLM** (OpenAI‑compatible) serving **Qwen3‑Embedding‑8B** on GPU for embeddings (chunks, facets, concepts).
  Example startup:

  ```bash
  export VLLM_API_BASE="http://127.0.0.1:8000"
  python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3-Embedding-8B \
    --task embedding \
    --dtype bfloat16 \
    --tensor-parallel-size 1 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.92 \
    --trust-remote-code
  # quick check:
  curl $VLLM_API_BASE/v1/embeddings -H 'Content-Type: application/json' \
    -d '{"model":"Qwen/Qwen3-Embedding-8B","input":"test"}'
  ```

  (Default embedding dimension: **4096**; plan vector‑index memory accordingly.)

* **SPLADE‑v3 doc‑side expansion** runs on GPU (Torch CUDA).

* **NVIDIA Container Toolkit** installed (Ubuntu 24.04) so Docker services can run with `--gpus all`.

---

# 2) INTERMEDIATE REPRESENTATION (IR) — MEDICINE‑TUNED

*(Schemas unchanged; MinerU provenance added for PDF flows.)*

## 2.1 Document schema (canonical)

```json
{
  "type": "Document",
  "doc_id": "ctg:NCT01234567#2024-09-01:1a2b3c4d5e6f",
  "source_uri": "https://...",
  "source_system": "ctgov|pmc|pubmed|dailymed|gudid|guideline",
  "media_type": "application/json|application/xml|text/html|application/pdf",
  "domain": "medicine",
  "language": "en",
  "created_at": "2024-09-01T08:15:30Z",
  "ingest_at": "2025-09-25T12:04:10Z",
  "meta": {
    "nct_id": "NCT01234567",
    "pmid": "12345678",
    "pmcid": "PMC12345",
    "doi": "10.1000/j.jmb.2020.01.001",
    "spl_setid": "abcd-efgh-...",
    "udi_di": "A123456789012345",
    "journal": "NEJM",
    "year": 2024,
    "phase": "Phase 3",
    "overall_status": "Completed",
    "study_type": "Interventional",
    "license": "CC-BY",
    "publisher": "WHO",
    "record_version": "2024-09-01",

    "parser": "native|mineru",
    "mineru_run_id": "uuid-or-null",
    "mineru_version": "x.y.z-or-null",
    "mineru_artifacts": {
      "markdown_uri": "s3://.../mineru/<doc_key>/md.json",
      "blocks_uri":   "s3://.../mineru/<doc_key>/blocks.json",
      "tables_uri":   "s3://.../mineru/<doc_key>/tables.html"
    }
  },
  "text_concat_info": {
    "bytes_len": 812345,
    "char_to_page_bbox_map_uri": "s3://bucket/doc_id/offset_map.json"
  }
}
```

## 2.2 Block schema (canonical)

```json
{
  "type": "Block",
  "doc_id": "ctg:NCT01234567#2024-09-01:1a2b3c4d5e6f",
  "block_id": "uuid-4",
  "page_no": 3,
  "path": "Results > Primary outcome > ¶2",
  "block_type": "heading|paragraph|list_item|clause|footnote|caption|eligibility|definition",
  "text": "Canonicalized UTF-8 string ...",
  "raw_text": "Original string ...",
  "start_char": 120345,
  "end_char": 120995,
  "bbox": [78, 109, 518, 140],
  "meta": {
    "speaker": null,
    "loinc_section": "34067-9",
    "section_label": "Indications and Usage",
    "eligibility_kind": "inclusion|exclusion",
    "arm_name": "Sac/Val 97/103 mg bid",
    "arm_type": "Experimental",
    "outcome_name": "Cardiovascular mortality",
    "outcome_type": "Primary",
    "time_frame": "up to 27 months"
  }
}
```

## 2.3 Table schema (canonical)

```json
{
  "type": "Table",
  "doc_id": "pmc:PMC12345#v1:aa11bb22cc33",
  "block_id": "uuid-4",
  "page_no": 7,
  "path": "Results > Adverse Events > Table 3",
  "rows": [
    [ { "text": "Hyperkalemia" }, { "text": "Grade 3-4" }, { "text": "12/250" }, { "text": "4.8%" }, { "text": "Intervention" } ],
    [ { "text": "Hyperkalemia" }, { "text": "Grade 3-4" }, { "text": "4/248"  }, { "text": "1.6%" }, { "text": "Comparator" } ]
  ],
  "html": "<table>...</table>",
  "start_char": 20012,
  "end_char": 20140,
  "bbox": [56, 480, 540, 720],
  "meta": {
    "units": "UCUM",
    "source": "MinerU|XML|HTML",
    "caption": "Adverse events by CTCAE grade",
    "arm_labels": ["Intervention","Comparator"],
    "denominators": {"Intervention":250,"Comparator":248}
  }
}
```

### Normalization & validation (unchanged)

* **Canonicalization**: UTF‑8, NFKC; do **not** rewrite semantics in `text`; keep `raw_text`.
* **Table**: resolve span→rectangular; parse numeric hints; keep HTML if parsing fails.
* **Span maps**: `char_to_page_bbox_map` persisted for provenance.
* **Validation**: JSON Schema; referential integrity; monotone offsets; `meta.loinc_section` implies `source_system='dailymed'`.

---

# 3) MINERU‑FIRST PDF PARSING — SEPARATE GPU‑ONLY STEP

*(Content preserved & expanded to include service boundary, commands, QA, and no auto transition.)*

## 3.1 Service boundary & invocation

* MinerU runs as its own **GPU‑only** script/service. It **does not** trigger chunking/embedding automatically.
* **Docker (Ubuntu 24.04) example:**

  ```bash
  docker run --rm --gpus all \
    -e REQUIRE_GPU=1 -e CUDA_VISIBLE_DEVICES=0 \
    -v /data/raw:/in -v /data/mineru:/out \
    ghcr.io/opendatalab/mineru:latest \
      mineru --input /in/<doc.pdf> --output /out/<doc_key> \
             --ocr auto --tables html
  ```

* **Pipeline commands (end‑to‑end)**:

  ```bash
  # 1) Download PDF (no auto)
  med ingest pdf --uri https://site/path/file.pdf --doc-key DOC123
  # ledger: status=pdf_downloaded

  # 2) MinerU (GPU-only)
  med mineru-run --from-ledger --filter doc_key=DOC123 \
    --in-bucket s3://bucket/raw --out-bucket s3://bucket/mineru \
    --gpus all --fail-if-no-gpu
  # -> artifacts + IR JSONL; ledger: status=pdf_ir_ready

  # 3) Start post-MinerU ops (GPU required for embedding)
  med postpdf-start --from-ledger --filter doc_key=DOC123 \
    --steps ir->chunk->facet->embed->index \
    --gpus all --fail-if-no-gpu
  ```

## 3.2 MinerU pipeline (clinical‑aware post‑processing)

1. Reading order extraction ON; OCR AUTO; tables→HTML; return Markdown + JSON blocks + offset map.
2. **Two‑column detection** & reflow if needed.
3. **Header/footer suppression** (repeated line detection).
4. **Hyphenation repair** (dictionary‑guarded).
5. **Caption linking** (figure proximity); **footnotes** preserved separately.
6. **Map to IR**: Headings→`Block(heading)`; paragraphs→`Block(paragraph)`; lists→`Block(list_item)`; tables→`Table` with normalized rows + HTML; compute `path`, `page_no`, `bbox`, `start/end` offsets.
7. **Clinical heuristics**: IMRaD labeling; section tags (Eligibility, Endpoints/Outcomes, AEs, Dosing, Warnings); table intent tags (HR/OR/RR/CI, AE/Grade patterns).

## 3.3 MinerU QA gates (abort on failure)

* Reading order sanity (≥85% ascending y‑coords per page).
* Header/footer removal verified across ≥60% pages.
* Table rectangularization success; else keep HTML with a parse‑failure flag.
* OCR coverage threshold; rerun OCR if needed.
* Delta between `raw_text` and `text` ≤ 5% (heuristic) to catch over‑zealous normalization.
* On fatal errors: mark ledger `mineru_failed`; **no** CPU fallback.

## 3.4 Outputs & provenance (into IR)

* Artifacts stored & linked in `Document.meta.mineru_artifacts` + `mineru_run_id`, `mineru_version`.
* `text_concat_info.char_to_page_bbox_map_uri` points to offset mapping for precise span provenance.

## 3.5 vLLM & SPLADE are **not** part of MinerU

* MinerU only prepares text/tables.
* **Embeddings** (Qwen via vLLM) and **SPLADE v3** expansion happen **after** `postpdf-start` during chunk/facet/embed/index stages—**and only with GPU available**.

---

# 4) SEMANTIC CHUNKING (MEDICINE) — GATED & GPU‑AWARE

*(All prior chunking logic retained; now explicitly gated for PDFs and explicitly GPU‑accelerated for coherence checks & embeddings.)*

## 4.0 Pipeline gates

* **Non‑PDF**: chunker runs immediately after IR (auto).
* **PDF**: chunker runs **only** when you invoke:

  ```bash
  med postpdf-start --from-ledger --filter status=pdf_ir_ready \
    --steps ir->chunk->facet->embed->index \
    --gpus all --fail-if-no-gpu
  ```

## 4.1 Feature extractors (per sentence & block) — unchanged

* Sentence embeddings via **Qwen (vLLM)** for coherence checks; token counts; clinical tagger (`pico_population|pico_intervention|…|eligibility|recommendation|lab_value`).
* Block signals: heading/table/section labels (IMRaD, LOINC sections, registry sections), eligibility kind, arm/outcome names.

## 4.2 Domain presets (targets; unchanged)

* **IMRaD**: target **600** (450–700), overlap **15%**.
* **Registry**: eligibility **200–350**, outcomes **300–450**, results **450–700**, AEs atomic; overlap **15%**.
* **SPL**: per LOINC section **350–550**; overlap **15%**.
* **Guidelines**: recommendation unit **250–500**; overlap **10%**.

**Coherence thresholds**: narrative `τ_coh=0.55`; bullets/definitions `0.50`.
**Intent switch guard**: prefer boundary on PICO/Result↔AE tag switches after half of target length.

## 4.3 Boundary rules (priority; unchanged)

1. **Hard start**: heading depth change; registry section change; SPL LOINC section change; table start; eligibility kind switch; outcome measure switch.
2. **Soft stop**: token cap (> T×1.15); coherence drop (`cos < τ_coh` and length ≥ T×0.5); intent switch after half target; **never** split a list item/citation or an endpoint/effect pair.
3. **Overlap**: carry last 15% sentences forward unless boundary aligns with a heading.

**Tables**: always atomic chunks; add **LLM table_digest** (scope, metrics, units, arms, deltas).

## 4.4 Algorithm (pseudocode; unchanged)

```python
def chunk_blocks(blocks, domain_profile):
    chunks = []
    cur = init_chunk()
    prev_sent_emb = None
    for b in blocks:
        if is_hard_boundary(b, cur):
            finalize(chunks, cur); cur = init_chunk(start_at=b)
        if b.type == 'Table':
            finalize(chunks, cur) if not cur.empty()
            chunks.append(make_table_chunk(b))
            cur = init_chunk(); continue
        for sent in split_sentences(b.text):
            s_emb = embed_qwen(sent)       # via vLLM; GPU-only
            s_tag = clinical_tag(sent)
            if might_split_endpoint_effect_pair(cur, sent):
                force_add(cur, sent, s_emb, s_tag); continue
            exceed = cur.tokens + tok_len(sent) > tgt * 1.15
            low_coh = (prev_sent_emb and cos(prev_sent_emb, s_emb) < tau_coh and cur.tokens > tgt*0.5)
            switch = (cur.majority_tag != s_tag) and cur.tokens > tgt*0.5
            if (exceed or (low_coh and not in_risky_context(cur)) or switch):
                finalize_with_overlap(chunks, cur, overlap=0.15)
                cur = init_chunk(start_at=b)
            add_sentence(cur, sent, s_emb, s_tag)
            prev_sent_emb = s_emb
    finalize_with_overlap(chunks, cur, overlap=0.15)
    return chunks
```

## 4.5 Clinical tagger (fast; unchanged)

* Weak supervision with keyword heuristics → train light classifier on Qwen sentence embeddings; rules override for strong cues (e.g., “Inclusion Criteria”, “Primary Outcome(s)”).

## 4.6 Facet summaries (per chunk; unchanged)

* Produce ≤120‑token **JSON** tuned to dominant intent (`pico`, `endpoint`, `ae`, `dose`, `eligibility`, `recommendation`, `general`), including **verbatim quotes + offsets** for every slot.
* Store `chunk.facet_json` and `chunk.facet_embedding_qwen` (embeddings via **vLLM**, GPU).

## 4.7 Embeddings & indexing (GPU‑forced; integrated)

* **Dense**: Qwen3‑Embedding‑8B via **vLLM** for `chunk.text` and `facet_json` → 4096‑dim vectors; stored on the chunk; **vector index** created later.
* **SPLADE‑v3**: **doc‑side expansion** on GPU (Torch) after chunking; store top‑K term weights per chunk; **query‑side expansion** at retrieval time.
* **BM25/BM25F**: index fields with boosts: `title_path:2.0`, `facet_json:1.5–1.6`, `table_lines:1.2`, `body:1.0`.
* **GPU checks**: if vLLM unreachable or GPU absent → **abort** and keep ledger consistent. No CPU fallback.

## 4.8 Robustness evaluation & fallbacks (unchanged)

**Intrinsic**: intra/inter coherence medians; boundary alignment; size distribution; no table/bullet splits.
**Extrinsic**: dev set across intents (`pico`, `endpoint`, `ae`, `dose`, `eligibility`, `recommendation`)—compute Recall@20, nDCG@10, MRR using **fusion** (BM25 + SPLADE + Qwen).
**Fallbacks (always enabled)**:

* **Multi‑granularity indexing** (paragraph / chunk / section) with **RRF** or weighted fusion.
* **Sliding windows** (512/768, 25% overlap) for problematic docs.
* **Neighbor merge** at query time for adjacent micro‑chunks.

## 4.9 Data structures in Neo4j & search (unchanged)

* `:Chunk { id, doc_id, text, type, section, tokens, start_char, end_char, facet_json, facet_type, embedding_qwen[], splade_terms{}, createdAt }`
* `(:Document)-[:HAS_CHUNK]->(:Chunk)`
* Optional `(:Chunk)-[:SIMILAR_TO {score, model, ver}]->(:Chunk)` for navigation (non‑authoritative).

## 4.10 Edge cases & guardrails (unchanged)

* **Composite endpoints**: keep components and first effect together when possible.
* **Dose titration**: prefer single chunk; if not, neighbor‑merge at query time.
* **Unit collisions**: keep original + UCUM normalized; never rewrite canonical `text`.
* **Negation/uncertainty**: tag facet with `negation=true` as needed.
* **Table notes/footnotes**: include within table chunk to preserve denominator/context.

---

## Quick‑start: GPU runbook (Ubuntu 24.04)

1. Install NVIDIA driver + CUDA; install NVIDIA Container Toolkit.
2. Start **vLLM** (Qwen3‑Embedding‑8B) and verify `/v1/embeddings`.
3. **Non‑PDF**: run `med ingest ctgov|pmc|spl ... --auto` to exercise the full DAG.
4. **PDF**: `med ingest pdf …` → `med mineru-run …` (GPU) → `med postpdf-start …` (GPU).
5. Monitor: ensure **no CPU fallback** occurred; if GPU unavailable, jobs must fail with exit **99** and clear diagnostics.

---

This integrated write‑up preserves every detail of the original Sections **1–4** and **seamlessly adds**:

* Explicit **two‑phase PDF handling** with **MinerU as a separate, manual GPU‑only step** (no auto transition).
* **Ledger‑driven gating** (`pdf_downloaded` → `pdf_ir_ready` → `postpdf-start`).
* **GPU enforcement** across MinerU, SPLADE‑v3, and Qwen3 via **vLLM** on **Ubuntu 24.04**, with **no CPU fallback**.
* Concrete **commands**, **env flags**, and **failure semantics** so your agents can implement exactly this behavior.

# 5) Medical ontologies, codes & IDs — **Concept Catalog**

## 5.0 Objectives

1. Build a **unified Concept Catalog** spanning diseases, phenotypes, labs, drugs, adverse events, and devices.
2. Normalize **labels, synonyms, definitions, identifiers, hierarchy**, and **cross‑walks** (UMLS when licensed).
3. Produce **three artifacts** per concept family:

   * **Neo4j nodes** (`:Concept` + typed labels, e.g., `:Condition`, `:Phenotype`, `:Drug`, `:Outcome`, `:AdverseEvent`, `:Device`).
   * **OpenSearch index** for **BM25 + SPLADE** (lexical/sparse).
   * **Vector store** of **Qwen3‑Embedding‑8B** for dense matching.
4. Version everything; keep **release metadata + license provenance**.

> **Licensing gates** must be enforced at ETL time and at query time for SNOMED CT, UMLS, and MedDRA content. MedDRA text cannot be redistributed; store only IDs + your own derived mappings in restricted contexts.

---

## 5.1 Sources & update cadence

| Family           | Primary source                                             | Format                | Cadence                   | Notes                                                                 |
| ---------------- | ---------------------------------------------------------- | --------------------- | ------------------------- | --------------------------------------------------------------------- |
| Conditions       | **ICD‑11**, **SNOMED CT**, **MONDO**, **MeSH Descriptors** | JSON/RDF/OWL/TSV/XML  | 2–4×/yr                   | Use MONDO to harmonize ICD/SNOMED; SNOMED requires affiliate license. |
| Phenotypes       | **HPO**                                                    | OBO/OWL + TSV         | monthly                   | Includes synonyms, definitions, disease associations.                 |
| Labs/Measures    | **LOINC** (+ **UCUM** units)                               | CSV/REL               | 2×/yr (LIVD updates vary) | Map LOINC ↔ UCUM; store components, properties, methods.              |
| Drugs/Substances | **RxNorm** (RxCUI), **UNII/GSRS**, **SPL**                 | RRF/RXNORM, JSON, XML | weekly/monthly            | Use RxNorm ingredients/brands/clinical drugs; UNII from GSRS.         |
| Adverse Events   | **MedDRA** (+ **CTCAE** grades)                            | MDB/CSV/PDF           | quarterly                 | MedDRA licensing; CTCAE mapping tables (v5.x).                        |
| Devices          | **AccessGUDID** / **openFDA UDI**                          | CSV/JSON              | continuous                | Extract UDI‑DI, brand, model, sterilization, MRI safety.              |
| IDs              | **NCT**, **PMID/PMCID**, **DOI**                           | Regex + NLM services  | continuous                | Deterministic extractors/validators.                                  |

**Updater service contract**

```yaml
# cron-like cadence per source (UTC)
catalog_updates:
  snomed_ct: "0 4 1 JAN,APR,JUL,OCT *"   # quarterly-ish; adjust to release
  icd11: "0 5 1 MAR,SEP *"
  mondo: "0 3 1 * *"
  hpo: "0 2 1 * *"
  loinc: "0 1 1 JAN,JUL *"
  rxnorm: "0 0 * * MON"
  gsrs_unii: "0 6 1 * *"
  meddra: "0 4 1 JAN,APR,JUL,OCT *"
  gudid: "0 */6 * * *"                   # every 6 hours
```

---

## 5.2 Canonical **Concept** data model

### 5.2.1 JSON Schema (`concept.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "concept.schema.json",
  "title": "Concept",
  "type": "object",
  "required": ["iri", "family", "label", "codes", "release"],
  "properties": {
    "iri": {"type": "string"},                // Stable IRI/URI (source's canonical IRI; else vendor-IRI)
    "family": {
      "type": "string",
      "enum": ["condition","phenotype","lab","drug","substance","outcome","adverse_event","device","literature_id"]
    },
    "label": {"type": "string"},
    "preferred_term": {"type": "string"},
    "synonyms": {
      "type": "array", "items": {
        "type": "object",
        "properties": {
          "value": {"type": "string"},
          "type": {"type": "string", "enum": ["exact","narrow","broad","related","brand","abbrev"]},
          "lang": {"type": "string", "default": "en"}
        },
        "required": ["value"]
      }
    },
    "definition": {"type": "string"},
    "codes": {
      "type": "array", "items": {
        "type": "object",
        "properties": {
          "system": {"type": "string"},    // e.g., "SNOMEDCT", "ICD11", "RxNorm", "UNII", "LOINC", "MedDRA", "HPO"
          "code": {"type": "string"},
          "display": {"type": "string"}
        },
        "required": ["system", "code"]
      }
    },
    "xrefs": {
      "type": "array", "items": {"type": "string"}   // e.g., UMLS CUI, MONDO xref, MeSH ID
    },
    "hierarchy": {
      "type": "object",
      "properties": {
        "parents": {"type": "array", "items": {"type": "string"}},
        "ancestors": {"type": "array", "items": {"type": "string"}}
      }
    },
    "attributes": {
      "type": "object", "additionalProperties": true  // LOINC parts, RxNorm TTY, UCUM canonical, etc.
    },
    "embedding_qwen": { "type": "array", "items": {"type": "number"} },  // 4096-D
    "splade_terms": {
      "type": "object",
      "additionalProperties": {"type": "number"}       // term -> weight
    },
    "release": {
      "type": "object",
      "properties": {
        "source": {"type": "string"},  // "SNOMED CT INT 2025-03-01"
        "version": {"type": "string"},
        "released_at": {"type": "string", "format": "date"}
      },
      "required": ["source","version"]
    },
    "license_bucket": {
      "type": "string",
      "enum": ["open","permissive","restricted","proprietary"]
    },
    "provenance": {
      "type": "object",
      "properties": {
        "ingested_at": {"type": "string", "format": "date-time"},
        "pipeline_ver": {"type": "string"},
        "source_uri": {"type": "string"}
      }
    }
  }
}
```

> **Hierarchies:** We store **parents** (direct) and **ancestors** (transitive) IRIs for quick inclusion/exclusion filtering and semantic boosts.

### 5.2.2 Neo4j node mapping

* **Labels:** `:Concept` plus specific type (`:Condition`, `:Phenotype`, `:Lab`, `:Drug`, `:Substance`, `:Outcome`, `:AdverseEvent`, `:Device`).
* **Key properties:** `iri`, `family`, `label`, `preferred_term`, `synonyms` (string[]), `definition`, `codes` (map[]), `release`, `license_bucket`, `embedding_qwen` (float[]), `splade_terms` (map), `attributes` (map).
* **Edges:**

  * `(:Concept)-[:IS_A]->(:Concept)` for taxonomy.
  * `(:Concept)-[:SAME_AS]->(:Concept)` for cross‑walk merges.
  * `(:Concept)-[:HAS_CODE {system, code}]->(:Identifier)` (optional if you also keep separate `:Identifier`).

**Constraints & indexes**

```cypher
CREATE CONSTRAINT concept_iri_unique IF NOT EXISTS FOR (k:Concept) REQUIRE k.iri IS UNIQUE;
CREATE VECTOR INDEX concept_qwen_idx IF NOT EXISTS FOR (k:Concept) ON (k.embedding_qwen)
OPTIONS { indexConfig: { `vector.dimensions`: 4096, `vector.similarity_function`: 'cosine' } };
```

---

## 5.3 OpenSearch indices (lexical + SPLADE)

### 5.3.1 **Concepts index** (name: `concepts_v1`)

**Settings (abridged)**

```json
{
  "settings": {
    "index": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "30s",
      "query": { "default_field": ["label^3", "synonyms.value^2", "definition"] },
      "similarity": { "bm25": { "k1": 0.9, "b": 0.35 } },
      "analysis": {
        "filter": {
          "biomed_syns": {
            "type": "synonym_graph",
            "lenient": true,
            "synonyms_path": "analysis/biomed_synonyms.txt"  // generated from Concept Catalog
          }
        },
        "analyzer": {
          "biomed": {
            "type": "custom",
            "char_filter": ["html_strip"],
            "tokenizer": "standard",
            "filter": ["lowercase", "asciifolding", "biomed_syns"]
          }
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "iri": { "type": "keyword" },
      "family": { "type": "keyword" },
      "label": { "type": "text", "analyzer": "biomed" },
      "preferred_term": { "type": "text", "analyzer": "biomed" },
      "synonyms": {
        "type": "nested",
        "properties": {
          "value": { "type": "text", "analyzer": "biomed" },
          "type": { "type": "keyword" }
        }
      },
      "definition": { "type": "text", "analyzer": "biomed" },
      "codes": {
        "type": "nested",
        "properties": { "system": {"type":"keyword"}, "code":{"type":"keyword"}, "display":{"type":"text"} }
      },
      "splade_terms": { "type": "rank_features" }   // term -> weight
    }
  }
}
```

> Populate `analysis/biomed_synonyms.txt` **from the Catalog** (exact + brand/generic, common abbreviations, Greek letter expansions, US/UK spellings). Regenerate on every catalog refresh.

### 5.3.2 SPLADE term storage

* Store doc‑side SPLADE expansions in `splade_terms` where each term’s weight is written as a **rank feature**.

**Example doc (abridged)**

```json
{
  "iri":"http://rxnorm.info/rxcui/198211",
  "family":"drug",
  "label":"enalapril",
  "synonyms":[{"value":"Vasotec","type":"brand"},{"value":"ACE inhibitor","type":"related"}],
  "definition":"... angiotensin-converting enzyme inhibitor ...",
  "codes":[{"system":"RxNorm","code":"198211"}],
  "splade_terms":{"enalapril":3.2,"ace":1.8,"inhibitor":1.1,"vasotec":2.0}
}
```

---

## 5.4 Dense embeddings (Qwen3‑Embedding‑8B)

* **Input text for embedding**: `label + "\n" + top-8 synonyms + "\n" + definition (<= 256 tokens)`.
* **Vector dim**: 4096; **similarity**: cosine.
* **Batching**: 256 concepts/batch (adjust to VRAM).
* **Dedup**: if identical `label+definition` across ontologies, compute once; share across IRIs (but keep distinct nodes).
* **Storage**:

  * **Neo4j** `embedding_qwen` for graph‑side similarity.
  * **Optional** FAISS (HNSW, M=64, efConstruction=400) if you need *very* large catalogs; keep `concept_id → vector_id` mapping.

---

## 5.5 ID extractors & validators

Implement **pure functions** with **deterministic behaviors**. Return `{valid: bool, norm: string, meta: {...}}`.

```ts
function isRxCUI(s: string): {valid:boolean, norm?:string} {
  // RxCUI is numeric (no fixed length, typically <= 9 digits)
  const m = s.match(/^\d{1,9}$/);
  return { valid: !!m, norm: m ? String(Number(s)) : undefined };
}

function isUNII(s: string): {valid:boolean, norm?:string} {
  // 10 uppercase alphanumerics
  const m = s.match(/^[A-Z0-9]{10}$/);
  return { valid: !!m, norm: m ? s : undefined };
}

function isNCT(s: string): {valid:boolean, norm?:string} {
  const m = s.match(/^NCT\d{8}$/i);
  return { valid: !!m, norm: m ? s.toUpperCase() : undefined };
}

function isDOI(s: string): {valid:boolean, norm?:string} {
  const m = s.match(/^10\.\d{4,9}\/[-._;()/:A-Z0-9]+$/i);
  return { valid: !!m, norm: m ? s.toLowerCase() : undefined };
}

function isLOINC(s: string): {valid:boolean, norm?:string} {
  // Standard LOINC numeric codes: N...N-D
  const m = s.match(/^\d{1,7}-\d$/);
  return { valid: !!m, norm: m ? s : undefined };
}

function isSNOMEDId(s: string): {valid:boolean, norm?:string} {
  // SNOMED uses Verhoeff check digit. Implement verifier.
  return { valid: verhoeffCheck(s), norm: s };
}

function isGS1GTIN14(s: string): {valid:boolean, norm?:string} {
  const m = s.match(/^\d{14}$/);
  if (!m) return {valid:false};
  return { valid: mod10Check(s), norm: s };   // for UDI DI with (01) GTIN
}
```

> **ICD‑11**: prefer table lookup to regex, because codes are not uniformly patternable. Validate by **present in release index**.

---

## 5.6 Catalog **build pipeline**

**DAG**: `download → parse → normalize → enrich (UMLS/xrefs) → merge → embed (SPLADE/Qwen) → write (Neo4j/OS/FAISS) → publish`.

**Key steps**

1. **Parse**: Source‑specific loaders produce interim JSON with `id`, `label`, `synonyms[]`, `definition`, `parents[]`, `codes[]`, `release`.
2. **Normalize text**:

   * Unicode NFC, lowercase for matching fields, preserve case in display.
   * Normalize Greek letters (α→alpha), common hyphenation variants, US/UK (anemia/anaemia), plurals (lemmatize), chemical salt stripping (`hydrochloride` recognized but not removed from display).
3. **Merge & cross‑walk**:

   * Prefer **MONDO** bridges for disease mappings; else UMLS CUIs.
   * Keep **all** source concepts; connect with `:SAME_AS` (with `evidence: "MONDO|UMLS|manual"`).
4. **License gating**:

   * Mark `license_bucket` and **exclude** restricted content from **public** OpenSearch synonyms file; keep them in secured indices.
5. **Embeddings**:

   * SPLADE doc‑side: tokenize with the model’s tokenizer; produce term:weight map, threshold by **top‑K=200** terms per concept.
   * Qwen dense vectors as above.
6. **Indexes**:

   * **OpenSearch** bulk index with BM25 + `rank_features` for SPLADE.
   * **Neo4j**: upsert nodes, build `:IS_A` edges, compute `ancestors` by DFS/BFS (or store only parents; compute ancestors dynamically if memory is tight).

**Idempotency**: Generate a catalog **release hash** (`SHA256` of concatenated source versions). Write to `provenance.pipeline_ver`.

---

## 5.7 Example **Concept** (drug)

```json
{
  "iri": "http://rxnorm.info/rxcui/198211",
  "family": "drug",
  "label": "Enalapril",
  "preferred_term": "enalapril",
  "synonyms": [
    {"value": "Vasotec", "type": "brand"},
    {"value": "ACE inhibitor", "type": "related"},
    {"value": "Enalapril maleate", "type": "exact"}
  ],
  "definition": "An angiotensin-converting enzyme inhibitor used to treat hypertension and heart failure.",
  "codes": [{"system": "RxNorm", "code": "198211"}],
  "xrefs": ["UMLS:C0014255"],
  "hierarchy": {"parents": ["MONDO:0004980"], "ancestors": []},
  "attributes": {"rxtty": "IN"},
  "splade_terms": {"enalapril": 3.21, "ace": 1.76, "vasotec": 2.02, "inhibitor": 1.08},
  "embedding_qwen": [/* 4096 floats */],
  "release": {"source": "RxNorm", "version": "2025-09-01", "released_at": "2025-09-01"},
  "license_bucket": "open",
  "provenance": {"ingested_at": "2025-10-02T00:00:00Z", "pipeline_ver": "catalog-1.0.3", "source_uri": "https://..." }
}
```

---

# 6) Retrieval & embeddings — **ingest‑time computation + runtime fusion**

## 6.0 Objectives

* Create **three parallel retrievers** (BM25/BM25F, SPLADE‑v3 sparse, Qwen3 dense) over **Chunks** and **Facet summaries**.
* Provide **stable, low‑variance fusion** (weighted linear or RRF) and optional **Qwen reranker** on top‑K.
* Ensure **traceability**: return **per‑model scores**, doc/chunk IDs, and **span contexts**.

---

## 6.1 Indexable objects & fields

**Primary objects** (from IR/chunking pipeline):

* `Chunk` (narrative or table‑atomic)
* `Facet` JSONs (pico/endpoint/ae/dose) as **auxiliary mini‑documents** referencing their `chunk_id`.

**Flattened index document** (OpenSearch `chunks_v1`):

```json
{
  "chunk_id": "uuid",
  "doc_id": "sha1:...",
  "title_path": "Methods > Randomization",
  "body": "canonicalized UTF-8 text of the chunk",
  "facet_json": "{\"population\":\"...\",\"intervention\":\"...\"}",
  "table_lines": ["Outcome\tHR\t0.76\t95% CI 0.61-0.95", "..."],  // if table chunk
  "meta": { "source":"pmc", "section":"Results", "pico":"result|outcome|..." },
  "embedding_qwen": [/* 4096 floats */],
  "splade_terms": {"hazard":1.2,"ratio":1.1,"hr":2.5, "0.76":0.7}
}
```

**BM25F boosts**: `title_path:2.0`, `facet_json:1.6`, `table_lines:1.2`, `body:1.0`.

**Separate indices**

* `chunks_v1` (full text, SPLADE rank_features).
* `concepts_v1` (from §5).
* Optional `facets_v1` (if you want independent facet routing).

---

## 6.2 OpenSearch mappings (chunks)

```json
{
  "settings": {
    "index": {
      "number_of_shards": 6,
      "number_of_replicas": 1,
      "similarity": { "bm25": { "k1": 0.9, "b": 0.35 } },
      "analysis": {
        "filter": {
          "biomed_syns": { "type":"synonym_graph", "lenient":true, "synonyms_path":"analysis/biomed_synonyms.txt" }
        },
        "analyzer": {
          "biomed": { "type":"custom", "tokenizer":"standard", "filter":["lowercase","asciifolding","biomed_syns"] }
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "chunk_id": {"type":"keyword"},
      "doc_id": {"type":"keyword"},
      "title_path": {"type":"text", "analyzer":"biomed"},
      "body": {"type":"text", "analyzer":"biomed"},
      "facet_json": {"type":"text", "analyzer":"biomed"},
      "table_lines": {"type":"text", "analyzer":"biomed"},
      "splade_terms": {"type":"rank_features"},
      "meta": {"type":"object", "enabled": true}
    }
  }
}
```

---

## 6.3 SPLADE‑v3 (sparse neural) — **offline doc expansion**

**Doc‑side pipeline**

1. Tokenize chunk text (and `facet_json` + `table_lines` concatenated with separators).
2. Run **naver/splade‑v3** in **document mode** to produce a **term→weight** map.
3. Keep top **K=400** terms per chunk, **min_weight ≥ 0.05**; L2‑normalize weights if desired for scoring stability.
4. Persist to OpenSearch `splade_terms` (rank_features).

**Query‑time**

* Use **query‑encoder** to expand query into weighted terms (on the fly).
* Construct an OS query with `rank_feature` clauses:

  ```json
  {
    "query": {
      "bool": {
        "should": [
          { "match": { "body": { "query": "<user text>", "analyzer":"biomed" } } },
          { "match": { "title_path": { "query": "<user text>", "boost": 2.0 } } },
          { "rank_feature": { "field": "splade_terms", "boost": 1.0 } }
        ]
      }
    }
  }
  ```

* (Or use a custom script_score combining BM25 and SPLADE; see fusion below.)

---

## 6.4 Dense embeddings — **Qwen3‑Embedding‑8B**

**Ingest‑time**

* Compute `embedding_qwen` for every `Chunk` (and optionally for **Facet mini‑docs**).
* Store in **Neo4j** (and/or FAISS). Create the vector index:

  ```cypher
  CREATE VECTOR INDEX chunk_qwen_idx FOR (c:Chunk) ON (c.embedding_qwen)
  OPTIONS { indexConfig: { `vector.dimensions`: 4096, `vector.similarity_function`: 'cosine' } };
  ```

**Query‑time**

* Embed query text (augmented with intent & synonyms, §11).
* KNN search in Neo4j: `CALL db.index.vector.queryNodes('chunk_qwen_idx', $k, $queryEmbedding)`.
* Return `(chunk_id, score_dense)`.

---

## 6.5 **Fusion** strategy & reranking

**Normalization**

* For each retriever, normalize scores to **[0,1]** per query using min‑max over the union of top‑K.
* Alternatively use **RRF** (Reciprocal Rank Fusion) with `k=60` for robustness.

**Weighted fusion** (default)

```
FusedScore = 0.50 * score_splade + 0.35 * score_dense + 0.15 * score_bm25
```

**Reranker (optional)**

* If latency budget allows, run **Qwen reranker** on **top‑100 fused** candidates.
* Input: `[ (query, candidate_text) ]` where `candidate_text = title_path + "\n" + first 600 chars`.
* Output: new scores in [0,1]; **replace** `FusedScore` with reranker score for final ranking, but **keep** component scores for telemetry.

**Pseudo‑code**

```python
def retrieve(query_text, k=20):
    bm = bm25_search(query_text, topN=200)         # (id, s_bm)
    sp = splade_search(query_text, topN=200)       # (id, s_sp)
    de = dense_knn(query_text, topN=200)           # (id, s_de)

    S = union_ids(bm, sp, de)
    norm = normalize_scores_to_01(S, bm, sp, de)
    fused = {id: 0.5*norm.sp[id] + 0.35*norm.de[id] + 0.15*norm.bm[id] for id in S}

    top = topk(fused.items(), 100)
    if CFG.rerank.enabled:
        ranked = qwen_rerank(query_text, top, return_top=k)
    else:
        ranked = topk(fused.items(), k)
    return enrich_with_spans_and_meta(ranked)
```

**Latency SLO** (P95 targets)

* BM25/SPLADE (OpenSearch): ≤ 200 ms
* Dense (Neo4j KNN, 4096‑D): ≤ 150 ms
* Fusion + (optional) rerank: ≤ 250 ms
* **Total P95** without rerank: ≤ 450 ms; with rerank: ≤ 700 ms

---

## 6.6 Observability & guardrails

* **Per‑component scores** + final fused score returned to client.
* **Feature flags**: toggle weights, turn off SPLADE if model down.
* **Caching**:

  * Query → embedding cache (60s).
  * Top‑N result cache key: hash(query + filters + modelVersions).
* **Drift**: monitor hit overlap vs last release; alert if overlap < 0.6.

---

# 7) Ontology‑aware search & mapping — **end‑to‑end EL + extraction**

## 7.0 Objectives

* Detect **mentions** (entities & IDs) with high recall.
* Generate **candidate concepts** via dictionary + neural retrieval.
* **Adjudicate** with an LLM using **span‑grounded context**.
* Extract **relations/events** (PICO, effects, AEs, dose, eligibility) with **codes** and **units**.
* Apply **clinical guardrails** (negation, uncertainty, temporality).

---

## 7.1 Mention detection (NER + dictionaries)

### 7.1.1 NER stack

* **scispaCy** pipeline (small/medium model for speed) with:

  * `en_core_sci_sm` (or `en_core_sci_md`) for base NER.
  * Add **custom heads** for `drug`, `dose`, `route`, `frequency`, `lab_value`, `adverse_event`, `eligibility`.
* **QuickUMLS** (if UMLS licensed):

  * Approximate string matcher over `label + synonyms` from **Concept Catalog** (not raw UMLS dump).
  * Jaccard threshold default **0.7**; include stemming; window sizes up to **6 tokens**.
* **Regex detectors** (deterministic IDs):

  * `RxCUI`, `UNII`, `NCT`, `DOI`, `LOINC`, **GTIN‑14** (UDI DI), **PMID/PMCID**.
* **Output (Mention)**:

```json
{
  "doc_id":"sha1:...",
  "chunk_id":"uuid",
  "start":1234,"end":1260,
  "text":"enalapril 10 mg twice daily",
  "type":"drug|condition|phenotype|lab|ae|device|id|dose|route|freq|eligibility|outcome",
  "features":{
    "normalized":"enalapril",
    "num":10,"unit":"mg","route":"PO","freq":"BID"
  }
}
```

### 7.1.2 Post‑processing

* **Span cleanup**: expand to include adjacent units (e.g., “mg”), collapse overlapping matches by **highest specificity** (e.g., “enalapril maleate” over “enalapril” if both backed by a concept).
* **Section‑aware filtering**: boost `ae` in **Adverse Reactions** sections (SPL), `eligibility` inside **Inclusion/Exclusion**.

---

## 7.2 Candidate generation (concept search)

For each mention **M**:

1. **Deterministic match**: if **ID** pattern valid (RxCUI/UNII/NCT/LOINC/GTIN), create candidate with score **1.0**.
2. **Dictionary candidates**:

   * Exact/normalized match against **label/synonyms** in `concepts_v1` (OpenSearch term/phrase query).
   * Use **field boosts**: `label^3`, `synonyms.value^2`, `definition^0.5`.
3. **SPLADE sparse**:

   * Build SPLADE query from **M.text** + section hints.
   * Retrieve top‑K=20 from `concepts_v1` using `rank_feature` scoring.
4. **Dense**:

   * Embed `M.context` (±2 sentences) with Qwen.
   * KNN search in **Neo4j concept_qwen_idx** (or FAISS) top‑K=20.

**Aggregate & score**

* Combine with **RRF (k=60)** to produce **top‑K=20** candidates.
* Attach candidate metadata: `iri`, `codes[]`, `label`, `synonyms[]`, `definition`, **source license bucket** (to display/hide text as needed).

**Candidate payload (to adjudicator)**

```json
{
  "mention": {"text":"enalapril 10 mg", "type":"drug", "context":"..."},
  "candidates": [
    {"iri":"rxnorm:198211","label":"Enalapril","codes":[{"system":"RxNorm","code":"198211"}], "definition":"...", "synonyms":["Vasotec","ACE inhibitor"]},
    {"iri":"rxnorm:637188","label":"Enalapril maleate", ...}
  ],
  "doc_meta":{"source":"spl","section":"Dosage"}
}
```

---

## 7.3 EL Adjudication — **LLM with span grounding**

### 7.3.1 Model & interface

* LLM: production‑grade (deterministic temperature **0.0–0.2**).
* **Function‑calling schema** (`el_adjudicator.schema.json`):

```json
{
  "chosen_id": "string",                // concept IRI or deterministic ID
  "ontology": "string",                 // "RxNorm","SNOMEDCT","HPO","LOINC","MedDRA","ICD11","MONDO","UNII","NCT","UDI"
  "score": 0.0,
  "evidence_span": {"doc_id":"string","chunk_id":"string","start":0,"end":0,"quote":"string"},
  "alternates": [
    {"iri":"string","ontology":"string","score":0.0,"why":"string"}
  ],
  "notes": "string"
}
```

### 7.3.2 Decision rules (post‑LLM)

* **Accept** if `score ≥ 0.70` **AND** (if applicable) ID validator passes.
* If **multiple** accepted with same ontology → choose **most specific** (deepest in hierarchy).
* If none accepted → create **review task** with top‑5 alternates.
* **Write‑back**:

  * Create `(:Chunk)-[:MENTIONS {confidence, start, end, quote}]->(:Concept)` if concept.
  * For deterministic IDs, create `(:Chunk)-[:HAS_IDENTIFIER]->(:Identifier {system, code})`.

### 7.3.3 Error handling

* If LLM fails or returns invalid JSON:

  * Retry **once**.
  * Fallback: **dictionary + deterministic ID** only, mark `confidence=0.49`.

---

## 7.4 Relation & event extraction (span‑grounded)

### 7.4.1 PICO (FHIR **EvidenceVariable** analogs)

**Input**: IMRaD Methods/Results chunks + ClinicalTrials.gov registry fields.

**Extractor contract**

* **Prompt** constrained to output **`pico.schema.json`** (already specified in plan).
* Must:

  * Map **conditions** → SNOMED/MONDO/HPO where possible.
  * Map **drugs** → RxCUI; **labs** → LOINC + **UCUM**.
  * Use **verbatim spans** for each top‑level field (`population`, `interventions`, `comparators`, `outcomes`, `timeframe`).
* **Edge creation**:

  * `(:EvidenceVariable)-[:HAS_POPULATION]->(:Condition|:Phenotype)`
  * `(:EvidenceVariable)-[:HAS_INTERVENTION]->(:Intervention)` where `:Intervention` is `:Drug|:Device|:Procedure`.
  * `(:EvidenceVariable)-[:HAS_OUTCOME]->(:Outcome)`

### 7.4.2 Effect measures (FHIR **Evidence** analogs)

**Scope**: HR/RR/OR/MD/SMD; CI; p; N; per‑arm sizes; model; time unit (UCUM).

**Parsing**

* Prefer **tables** (atomic chunks); else sentences with patterns like:

  * “HR 0.76, 95% CI 0.61–0.95; p=0.012”.
* **Numeric normalization**:

  * Convert Unicode en‑dash to “-”, decimal commas to dots.
  * **CI parsing**: accept `a–b`, `a - b`, `(a, b)`.
* **Units**: if time‑to‑event, capture **time_unit_ucum** (e.g., `mo`).

**Write‑back**

* Node `:Evidence {type, value, ci_low, ci_high, p_value, n_total, arm_sizes, model, time_unit_ucum}`
* Edge `(:Document|:Study)-[:REPORTS]->(:Evidence)`
* Edge `(:Evidence)-[:MEASURES]->(:Outcome {loinc})`
* Edge `(:Evidence)-[:DEFINES]->(:EvidenceVariable)`

### 7.4.3 Adverse events (MedDRA + CTCAE)

**Detection**

* Find AE **tables** or narrative within **Adverse Events/Warnings** sections.

**Mapping**

* Mention → **MedDRA PT** (preferred term); include **LLT** if only LLT present.
* **CTCAE grade** if explicitly given; else leave `grade: null`.

**Counts**

* Extract per‑arm counts and denominators; compute rate if both present.

**Write‑back**

* Node `:AdverseEvent {meddra_pt, grade, count, denom, rate}`
* Edge `(:Arm|:Study)-[:HAS_AE]->(:AdverseEvent)` (attach `arm_id` when available)
* Evidence spans on the relationship property: `{doc_id,start,end,quote}`

### 7.4.4 Dose/route/schedule normalization

**Grammar**

* `{amount, unit (UCUM), route, frequency_per_day, duration}`

**Normalization rules**

* Map routes to standard list (`PO`, `IV`, `IM`, `SC`, `TOP`, `INH`…).
* Frequency parsing:

  * “BID”→2, “TID”→3, “QID”→4, “q8h”→3, “once daily”→1
* Duration: parse “x days/weeks/months” → UCUM (`d`, `wk`, `mo`), store canonical **days** as integer too.

**Write‑back**

* Node `:Intervention` if not exists; property `drug_rxcui` or `unii`.
* Edge `(:EvidenceVariable)-[:HAS_DOSE {amount, unit, route, frequency_per_day, duration_days, loinc_section}] -> (:Intervention)`

### 7.4.5 Eligibility constraints

**Split** Inclusion vs Exclusion by headers and bullets.

**Normalization**

* **Age**: to years (numeric range).
* **Labs**: `loinc`, `op` (`>=, >, <=, <, =`), `value`, `unit (UCUM)`, and normalized value to **canonical UCUM**.
* **Conditions**: map to SNOMED/MONDO/HPO.
* **Temporal**: detect windows: “within 3 months” → `{op: "<=", unit: "d", value: 90}`.

**Write‑back**

* Node `:EligibilityConstraint {type, logic_json}` with verbatim spans.
* Edge `(:Study)-[:HAS_ELIGIBILITY]->(:EligibilityConstraint)`

---

## 7.5 Clinical NLP guardrails

* **Negation & Uncertainty**:

  * Implement **ConText/NegEx** style rules over detected mentions.
  * Tag mention as `negated` or `hypothetical` → **do not** produce mappings unless section suggests otherwise (e.g., **Exclusion** lists negated conditions as *required absent* → still record in eligibility with `type: exclusion`).
* **Temporality**:

  * Heuristics for **past medical history** vs **adverse event during treatment** (use section/tense cues).
* **Co‑reference**:

  * Lightweight resolution for drug/pronoun references within a chunk (e.g., “the study drug”).

---

## 7.6 Endpoints / APIs (internal)

### 7.6.1 `POST /map/candidates`

**Request**

```json
{"doc_id":"sha1:...", "chunk_id":"uuid", "mentions":[{"start":123,"end":138,"text":"enalapril 10 mg","type":"drug"}]}
```

**Response**

```json
{
  "candidates":[
    {"mention_span":[123,138],"topK":[{"iri":"rxnorm:198211","score":0.91},{"iri":"rxnorm:637188","score":0.79}]}
  ]
}
```

### 7.6.2 `POST /map/el` (adjudicate)

* **Input**: candidates + 2–3 sentence context.
* **Output**: as `el_adjudicator.schema.json`.

### 7.6.3 `POST /extract/{pico|effects|ae|dose|eligibility}`

* **Input**: chunk IDs or entire document.
* **Output**: **strict schemas** already defined in plan (Section 10).

### 7.6.4 `POST /kg/write`

* Upsert concepts if missing; then create span‑grounded edges/nodes.

---

## 7.7 Validation & testing

### 7.7.1 Unit tests

* **ID validators** with positive/negative sets.
* **Dose grammar**: “10 mg bid x 14 days” → `{amount:10, unit:"mg", frequency_per_day:2, duration_days:14}`.
* **LOINC thresholds**: “eGFR ≥ 45 mL/min/1.73m2” → `{loinc:"48642-3", op:">=", value:45, unit:"mL/min/1.73m2"}`.

### 7.7.2 Integration tests

* Given a known trial abstract (gold PICO), ensure **PICO completeness ≥ 0.85**.
* Given an AE table (gold MedDRA PT + grade), ensure **≥ 0.80** mapping accuracy.

### 7.7.3 SHACL/Schema checks

* **Units** conform to **UCUM**.
* **Codes** exist in Concept Catalog for the declared system/version.

---

## 7.8 Security & license enforcement

* **ACL tags per concept**: `license_bucket`.
* Query layer must **filter** or **mask** any restricted labels/synonyms/definitions if caller lacks entitlement.
* **Audit log**: every EL or extraction write includes `{user_or_service, model, version, timestamp, prompt_hash}`.

---

## 7.9 Worked example (end‑to‑end)

**Input chunk (Results):**

> “The primary endpoint was all‑cause mortality (HR 0.76; 95% CI 0.61–0.95; p=0.012) with sacubitril/valsartan vs enalapril.”

1. **Mentions**:

   * `all‑cause mortality` → type `outcome`
   * `HR 0.76; 95% CI 0.61–0.95; p=0.012` → `effect`
   * `sacubitril/valsartan` → `drug`
   * `enalapril` → `drug`
2. **Candidates**:

   * Outcome → **LOINC** candidates for “All-cause mortality”; fallback to **MeSH** concept if LOINC unavailable.
   * Drugs → RxCUI candidates.
3. **Adjudication**:

   * Picks `RxCUI:1737755` (sacubitril/valsartan) and `RxCUI:198211` (enalapril).
4. **Effect extraction**:

   * `{type:"HR", value:0.76, ci_low:0.61, ci_high:0.95, p_value:0.012}`
5. **KG write**:

   * `:Evidence` node + `:Outcome` node (LOINC if found) + `:EvidenceVariable` PICO with `Intervention` & `Comparator`.
   * Spans attached to every numeric field.

---

## 7.10 Performance notes

* **Mention detection** target: ≥ **2,000 tokens/s/GPU** with batched scispaCy + regex; QuickUMLS on CPU with caching.
* **EL adjudication**: batch candidates by **document**; cap **20 candidates/mention**, **max 300 mentions/doc** per pass.
* **Fallbacks**: if LLM budget exceeded, accept deterministic IDs and top dictionary hit with `confidence=0.6`.

---

# Deliverables for Agents

1. **Schemas**

   * `concept.schema.json`
   * `el_adjudicator.schema.json`
2. **OpenSearch templates**

   * `concepts_v1.template.json`
   * `chunks_v1.template.json`
3. **Neo4j DDL**

   * Constraints + vector index statements listed above.
4. **ETL pipelines**

   * Source loaders (`snomed_loader.py`, `icd11_loader.py`, `mondo_loader.py`, `hpo_loader.py`, `loinc_loader.py`, `rxnorm_loader.py`, `gsrs_loader.py`, `meddra_loader.py`, `gudid_loader.py`).
   * Normalizers (`text_norm.py`, `units_ucum.py`, `dose_parser.py`, `id_validators.py`).
   * Embedders (`splade_doc_expander.py`, `qwen_embedder.py`).
5. **Services**

   * `catalog_updater` (cron + idempotent).
   * `retrieval_service` (BM25/SPLADE/Dense + fusion + rerank).
   * `mapping_service` (`/map/candidates`, `/map/el`).
   * `extraction_service` (`/extract/*`).
   * `kg_writer` (Neo4j upserts, span‑grounded).
6. **QA packs**

   * Unit tests for validators and parsers.
   * Gold sets for PICO, effects, AEs.
   * SHACL shapes for UCUM and code existence.

Below is an **agent‑ready**, engineering‑grade expansion of **Sections 8–10**. It specifies data shapes, algorithms, validation, storage, and write paths so it can be implemented without further clarification. It assumes all upstream objects (IR `:Document`, `:Block`, `:Table`, `:Chunk`) already exist.

---

# 8) Medical chunk **facet summaries** — implementation details

## 8.0 Overview

**Purpose:** For each `:Chunk`, generate compact, machine‑actionable JSON “facets” to enable **intent‑targeted retrieval** and **precise graph writes**. Facets are **≤120 tokens** each, **span‑grounded**, ontology‑linked where possible, and stored both (a) inline on the `:Chunk` node for indexing, and (b) emitted as normalized records for downstream extractors/KG writers.

**Facet types (v1.0‑med):**

* `facet:pico` — trial-like PICO micro‑summary
* `facet:endpoint` — outcome + effect metric
* `facet:ae` — adverse event row/statement
* `facet:dose` — normalized dosing statement

> **Note:** Additional internal facets may be produced opportunistically (e.g., `facet:eligibility`, `facet:design`) but **only** the four above are indexed in v1.0‑med.

---

## 8.1 Inputs

* `Chunk` object with:

  * `chunk_id`, `doc_id`, `text`, `path`, `block_type_distribution`, `meta` (e.g., `loinc_section`, `nct_id`, `pmid`)
  * `table_html`/`table_rows` when atomic table chunk
  * `span_map` from IR for char offsets ↔ page/bbox
* Concept Lexicon services (Section 5): `resolve_condition`, `resolve_drug`, `resolve_lab`, `resolve_meddra`, `resolve_units`
* Sentence‑level clinical tags from 4.1 (`pico_*`, `adverse_event`, `dose`, `eligibility`, `result`)

---

## 8.2 Facet detection (routing)

A light classifier assigns **candidate facet types** to each chunk before generation.

**Rules (deterministic first, then ML):**

1. **SPL sections (LOINC):**

   * `Indications [34067-9]` ⇒ prefer `facet:pico`
   * `Dosage and administration [34066-1]` ⇒ `facet:dose`
   * `Adverse reactions [34084-4]` ⇒ `facet:ae`
2. **ClinicalTrials.gov:**

   * `Outcome Measures` path ⇒ `facet:endpoint`
   * `Eligibility` path ⇒ (internal) `facet:eligibility`
3. **Table cues:** header contains any of `{Outcome, HR, OR, RR, Rate ratio, Incidence, Grade, Adverse, AE}` ⇒ try `endpoint` or `ae` depending on vocabulary; presence of `Arm/Group` columns tips to `ae`.
4. **Classifier:** A fast linear/Tree‑based model over n‑grams + sentence tags outputs probabilities for `[pico, endpoint, ae, dose]`. Thresholds:

   * If a rule fired: accept that facet.
   * Else accept any class with `p ≥ 0.55` (tie‑break by `endpoint > ae > dose > pico`).

Emit **0–N** facets per chunk (common: 1–2).

---

## 8.3 LLM extraction prompts (facet generators)

Each facet has a **strict JSON** output with **verbatim evidence spans**. All prompts include `doc_id`, `chunk_id`, `text`, and—if present—`table_rows` (row‑wise text). They **forbid inference** beyond provided text.

### 8.3.1 `facet:pico` prompt skeleton

* **System:** “You are extracting PICO from medical text. Output compact JSON under 120 tokens, include evidence spans (char start/end) relative to the provided chunk text.”
* **User payload:** `{text, doc_id, chunk_id, path, hints:{nct_id, loinc_section}}`
* **Required fields:** `population`, `intervention`, `comparator?`, `outcomes[]`, `timeframe?`, `evidence_spans[]`
* **Ontology hooks:** call `resolve_condition`, `resolve_drug`, `resolve_lab` post‑LLM on extracted labels.

### 8.3.2 `facet:endpoint` prompt skeleton

* Extract a **single** outcome measure with metric, CI, p‑value, N.
* Normalize `type ∈ {HR, RR, OR, MD, SMD}`.
* Prefer **numeric CI**; if CI text like “0.61–0.95”, split into floats.

### 8.3.3 `facet:ae` prompt skeleton

* Map AE term to **MedDRA PT**; prefer PT over LLT.
* Extract `grade` if present; else omit.
* Require `arm` (infer from column/label) and counts/denominator if available.

### 8.3.4 `facet:dose` prompt skeleton

* Normalize to `{amount, unit(UCUM), route, frequency_per_day, duration_days?}`.
* Route and form (e.g., “PO”, “IV infusion”) appear in `route` or `method`.
* Map drug to **RxCUI**/**UNII** where possible.

**Guardrails common to all prompts**

* “If a field is not present **verbatim**, omit it.”
* “Return only JSON (no comments).”
* “Include `evidence_spans` with `start`, `end`, `quote`.”
* “Do not fabricate arm names, grades, or codes.”

---

## 8.4 JSON Schemas (validation)

> **All schemas versioned**. Place under `/schemas/facets/v1/…`. Use `$defs` for shared types.

### 8.4.1 `facet.common.json`

```json
{
  "$id": "facets.common.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Span": {
      "type": "object",
      "required": ["start", "end", "quote"],
      "properties": {
        "start": {"type": "integer", "minimum": 0},
        "end": {"type": "integer", "minimum": 0},
        "quote": {"type": "string", "minLength": 1}
      }
    },
    "Code": {
      "type": "object",
      "required": ["system", "code"],
      "properties": {
        "system": {
          "type": "string",
          "enum": ["SNOMED", "ICD11", "MONDO", "HPO", "LOINC", "RxCUI", "UNII", "MedDRA", "UCUM", "NCT", "DOI", "PMID", "PMCID", "UDI"]
        },
        "code": {"type": "string", "minLength": 1},
        "display": {"type": "string"}
      }
    }
  }
}
```

### 8.4.2 `facet.pico.v1.json`

```json
{
  "$id": "facet.pico.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["population", "intervention", "outcomes", "evidence_spans"],
  "properties": {
    "population": {"type": "string", "minLength": 1},
    "population_codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}},
    "intervention": {"type": "string"},
    "intervention_codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}},
    "comparator": {"type": "string"},
    "comparator_codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}},
    "outcomes": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["name"],
        "properties": {
          "name": {"type": "string"},
          "loinc": {"type": "string"},
          "codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}}
        }
      }
    },
    "timeframe": {"type": "string"},
    "evidence_spans": {"type": "array", "minItems": 1, "items": {"$ref": "facets.common.v1.json#/$defs/Span"}},
    "token_budget": {"type": "integer", "const": 120}
  }
}
```

### 8.4.3 `facet.endpoint.v1.json`

```json
{
  "$id": "facet.endpoint.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["name", "type", "value", "evidence_spans"],
  "properties": {
    "name": {"type": "string"},
    "type": {"type": "string", "enum": ["HR", "RR", "OR", "MD", "SMD"]},
    "value": {"type": "number"},
    "ci_low": {"type": "number"},
    "ci_high": {"type": "number"},
    "p": {"type": ["number","string"]},
    "n_total": {"type": "integer", "minimum": 1},
    "arm_sizes": {
      "type": "object",
      "properties": {
        "int": {"type": "integer", "minimum": 1},
        "comp": {"type": "integer", "minimum": 1}
      },
      "additionalProperties": false
    },
    "model": {"type": "string"},
    "time_unit_ucum": {"type": "string"},
    "outcome_codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}},
    "evidence_spans": {"type": "array", "minItems": 1, "items": {"$ref": "facets.common.v1.json#/$defs/Span"}},
    "token_budget": {"type": "integer", "const": 120}
  }
}
```

### 8.4.4 `facet.ae.v1.json`

```json
{
  "$id": "facet.ae.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["term", "evidence_spans"],
  "properties": {
    "term": {"type": "string"},
    "meddra_pt": {"type": "string"},
    "grade": {"type": "string", "pattern": "^[1-5]$"},
    "arm": {"type": "string"},
    "count": {"type": "integer", "minimum": 0},
    "denom": {"type": "integer", "minimum": 0},
    "serious": {"type": "boolean"},
    "onset_days": {"type": "integer", "minimum": 0},
    "evidence_spans": {"type": "array", "minItems": 1, "items": {"$ref": "facets.common.v1.json#/$defs/Span"}},
    "token_budget": {"type": "integer", "const": 120}
  }
}
```

### 8.4.5 `facet.dose.v1.json`

```json
{
  "$id": "facet.dose.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["drug_label", "amount", "unit", "route", "evidence_spans"],
  "properties": {
    "drug_label": {"type": "string"},
    "drug_codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}},
    "amount": {"type": ["number", "string"]},
    "unit": {"type": "string"},            // UCUM
    "route": {"type": "string"},
    "frequency_per_day": {"type": "number", "minimum": 0},
    "duration_days": {"type": "number", "minimum": 0},
    "loinc_section": {"type": "string"},
    "evidence_spans": {"type": "array", "minItems": 1, "items": {"$ref": "facets.common.v1.json#/$defs/Span"}},
    "token_budget": {"type": "integer", "const": 120}
  }
}
```

---

## 8.5 Normalization & ontology mapping

**Post‑LLM normalizers** (pure functions; idempotent):

* **Numbers:** strip thousands separators; parse “0.61–0.95” ⇒ `ci_low=0.61`, `ci_high=0.95`; “p<0.001” ⇒ `p=".<0.001"`.
* **Units:** map to **UCUM** via lookups (e.g., “mg q12h” ⇒ `amount=...`, `frequency_per_day=2`); accept compact notations (e.g., `mL/min/1.73m2` ⇒ UCUM `mL/min/{1.73_m2}`).
* **Routes:** normalize synonyms (`PO`→`oral`, `IV`→`intravenous`), but keep **verbatim** in evidence.
* **Drugs:** `resolve_drug(label) → [RxCUI, UNII]` with confidence; attach to `drug_codes`.
* **Outcomes/Labs:** `resolve_lab(name) → LOINC?`; if unknown, keep `name` only.
* **AEs:** `resolve_meddra(term)` to PT (prefer PT; fallback LLT).

**Confidence/acceptance:**

* Keep a hidden `__confidence` score per facet (0–1) from resolver voting.
* **Drop** auto‑codes with `__confidence < 0.5` (still retain textual fields).

---

## 8.6 Token budget enforcement (≤120 tokens)

* Count tokens using the embedding model tokenizer (Qwen3). If >120:

  1. Drop optional fields in priority order: narrative text → codes → model → arm sizes.
  2. Compress ranges (`ci` as numbers only, remove spaces).
  3. Abbreviate routes (`PO`, `IV`) if not mandated otherwise.
* **Never** drop `evidence_spans`.

---

## 8.7 Storage & indexing

### 8.7.1 On `:Chunk` node (Neo4j)

* Properties:

  * `c.facet_pico_v1` (String; JSON)
  * `c.facet_endpoint_v1` (List<String>; multiple allowed)
  * `c.facet_ae_v1` (List<String>)
  * `c.facet_dose_v1` (List<String>)
  * `c.facets_model_meta` (Map: `{model, version, prompt_hash, ts}`)

> Rationale: easy retrieval fusion (BM25/SPLADE reads JSON strings via `facet_json` field in OpenSearch; store a **copy** there, too).

### 8.7.2 Search indexes

* **OpenSearch/ES**:

  * `facet_json` (copy of all facet JSON strings; `keyword` + `text` multi‑fields)
  * `facet_type` (`pico|endpoint|ae|dose`)
  * `facet_codes` (`codes.code` as `keyword`)
  * BM25F boosts per Section 11
* **SPLADE doc‑side expansion** applied to `body + title_path + facet_json + table_lines`.
* **Dense vectors** (Qwen) computed over:

  * Full chunk text, and
  * Facet JSON (minified string) → stored as `c.embedding_qwen` only for chunk text; **facet embeddings** optional (off by default to save space).

---

## 8.8 Dedupe & consolidation

* **Keyed dedupe** per Document for `facet:endpoint`: `(normalized_outcome_name|loinc, type, timeframe?)`.
* **AE row dedupe:** `(meddra_pt|term_lower, grade?, arm?)`.
* Keep all originals but mark `is_primary=true` on the highest confidence.

---

## 8.9 QA & failure handling

* **Schema validation**: reject non‑conforming JSON; log with `reason`.
* **Span verification**: every `evidence_spans[*]` must be within `[0, len(text))`.
* **Unit sanity**: dose `amount` must be numeric parseable if `unit` present; else drop `unit`.
* **Escalation**: chunks with 3 consecutive facet failures go to manual review queue.

---

# 9) KG schema (CDKO‑Med) & FHIR alignment — implementation details

## 9.0 Overview

We materialize a **span‑grounded, provenance‑rich** KG in Neo4j. `:Chunk` and `:Document` are the **anchors**; medical entities are **conceptual nodes** with standard codes. Evidence objects follow FHIR semantics.

---

## 9.1 Node labels & properties

> All nodes carry `created_at`, `updated_at`, `source`, `ver`, and `provenance` (activity id). Strings are UTF‑8; prefer short snake_case prop names.

### 9.1.1 Textual

* `:Document`

  * `uri` (UNIQUE), `doc_id`, `domain="medicine"`, `media_type`, `language`, `license`
  * `meta` (Map: may include `nct_id`, `pmid`, `pmcid`, `spl_setid`, `device_udi_di`)
* `:Chunk`

  * `id` (UNIQUE), `doc_id`, `path`, `block_types` (list), `text`, `start_char`, `end_char`, `page_no`
  * `facet_*_v1` (see 8.7.1), `embedding_qwen` (vector), `model_meta` (Map)
  * Optional: `table_html` (string), `table_digest_v1` (string JSON)

### 9.1.2 Study & design

* `:Study` — ClinicalTrials.gov alignment

  * `nct_id` (UNIQUE), `title`, `status`, `phase`, `enrollment`, `start_date`, `completion_date`, `design_info` (Map)

* `:Arm`

  * `name`, `type` (`experimental|active_comparator|placebo|...`), `size` (int)

### 9.1.3 Interventions

* `:Drug`

  * `label`, `rxcui` (UNIQUE), `unii` (optional), `atc` (optional list)

* `:Device`

  * `label`, `udi_di` (UNIQUE), `brand`, `model`

* `:Procedure`

  * `label`, `snomed` (code)

### 9.1.4 Clinical concepts

* `:Condition` — prefer MONDO & SNOMED

  * `label`, `mondo?`, `snomed?`, `icd11?`, `mesh?`

* `:Phenotype` (HPO)

  * `label`, `hpo` (code)

* `:Outcome`

  * `label`, `loinc` (UNIQUE when code present), `unit_ucum?`

* `:AdverseEvent` (MedDRA)

  * `pt` (Preferred Term), `pt_code` (MedDRA), `llt?`

* `:EligibilityConstraint`

  * `type` (`inclusion|exclusion`), `logic_json` (string JSON), `human_text`

### 9.1.5 Evidence & variables

* `:Evidence` (FHIR‑like)

  * `id` (UNIQUE local), `type` (`HR|RR|OR|MD|SMD`), `value` (float),
  * `ci_low?`, `ci_high?`, `p_value?`, `n_total?`,
  * `arm_sizes_json?`, `model?`, `time_unit_ucum?`, `certainty?` (`high|moderate|low|very-low`)
  * `spans_json` (string JSON array of spans)
* `:EvidenceVariable` (PICO component bundle)

  * `id` (UNIQUE), `population_json`, `interventions_json`, `comparators_json`, `outcomes_json`, `timeframe?`, `spans_json`

### 9.1.6 Identifiers & orgs

* `:Identifier` — generic

  * `scheme` (`NCT|PMID|PMCID|DOI|RxCUI|UNII|UDI|LOINC|SNOMED|ICD11|HPO|MedDRA|MONDO`)
  * `value` (UNIQUE per scheme)
* `:Organization`

  * `name`, `type`, `country`
* `:ExtractionActivity` (PROV)

  * `id` (UNIQUE), `model`, `version`, `prompt_hash`, `schema_hash`, `ts` (ISO8601)

---

## 9.2 Relationships & required properties

* `(:Document)-[:HAS_CHUNK]->(:Chunk)`
* `(:Study)-[:HAS_ARM]->(:Arm)`
* `(:Arm)-[:USES_INTERVENTION]->(:Drug|:Device|:Procedure)`
* `(:Study|:Document)-[:ABOUT]->(:Condition|:Intervention|:Outcome)`
* `(:Chunk)-[:MENTIONS {confidence, start, end, quote}]->(:Concept subtype)`
  *Use `:Condition|:Drug|:Outcome|:AdverseEvent` etc.*
* `(:Study|:Document)-[:REPORTS]->(:Evidence)`
* `(:Evidence)-[:DEFINES]->(:EvidenceVariable)`
* `(:Arm|:Study)-[:HAS_AE]->(:AdverseEvent) {grade?, count?, denom?, serious?, onset_days?}`
* `(:Study)-[:HAS_ELIGIBILITY]->(:EligibilityConstraint)`
* `(:Any)-[:HAS_IDENTIFIER]->(:Identifier)`
* `(:Any)-[:WAS_GENERATED_BY]->(:ExtractionActivity)`
  *(Mandatory for Evidence, EvidenceVariable, EligibilityConstraint)*

> **Navigation:** optional `(:Chunk)-[:SIMILAR_TO {score, model_ver}]-(:Chunk)` undirected.

---

## 9.3 Constraints, indexes & vector config (Neo4j)

**Uniqueness (idempotent writes):**

```cypher
CREATE CONSTRAINT doc_uri_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.uri IS UNIQUE;
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT study_nct_unique IF NOT EXISTS FOR (s:Study) REQUIRE s.nct_id IS UNIQUE;
CREATE CONSTRAINT drug_rxcui_unique IF NOT EXISTS FOR (d:Drug) REQUIRE d.rxcui IS UNIQUE;
CREATE CONSTRAINT device_udi_unique IF NOT EXISTS FOR (x:Device) REQUIRE x.udi_di IS UNIQUE;
CREATE CONSTRAINT outcome_loinc_unique IF NOT EXISTS FOR (o:Outcome) REQUIRE o.loinc IS UNIQUE;
CREATE CONSTRAINT identifier_scheme_value_unique IF NOT EXISTS
FOR (i:Identifier) REQUIRE (i.scheme, i.value) IS UNIQUE;
CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT evvar_id_unique IF NOT EXISTS FOR (v:EvidenceVariable) REQUIRE v.id IS UNIQUE;
```

**Vector index (Qwen3‑Embedding‑8B; cosine):**

```cypher
CREATE VECTOR INDEX chunk_qwen_idx
FOR (c:Chunk) ON (c.embedding_qwen)
OPTIONS { indexConfig: { `vector.dimensions`: 4096, `vector.similarity_function`: 'cosine' } };
```

**Fulltext (helpful for dev & fallback):**

```cypher
CALL db.index.fulltext.createNodeIndex(
  'chunk_text_ft', ['Chunk'], ['text', 'path'], { analyzer: 'english' }
);
```

---

## 9.4 Write patterns (MERGE templates)

> **All writes are performed via MERGE + SET** with deterministic keys. APOC `apoc.merge.node/relationship` can batch merges from facet payloads.

### 9.4.1 Attach `:Chunk` facets

```cypher
MERGE (c:Chunk {id: $chunk_id})
SET c.facet_pico_v1 = $pico_json? ,
    c.facet_endpoint_v1 = coalesce(c.facet_endpoint_v1, []) + $endpoint_jsons?,
    c.facet_ae_v1 = coalesce(c.facet_ae_v1, []) + $ae_jsons?,
    c.facet_dose_v1 = coalesce(c.facet_dose_v1, []) + $dose_jsons?,
    c.model_meta = $model_meta,
    c.updated_at = timestamp();
```

### 9.4.2 Create `:EvidenceVariable` and link

```cypher
MERGE (v:EvidenceVariable {id: $evvar_id})
SET v.population_json = $population_json,
    v.interventions_json = $interventions_json,
    v.comparators_json = $comparators_json,
    v.outcomes_json = $outcomes_json,
    v.timeframe = $timeframe,
    v.spans_json = $spans_json
WITH v
MATCH (d:Document {doc_id: $doc_id})
MERGE (d)-[:REPORTS]->(v)
```

### 9.4.3 Create `:Evidence` and connect to outcome & EV

```cypher
MERGE (e:Evidence {id: $evidence_id})
SET e.type=$type, e.value=$value, e.ci_low=$ci_low, e.ci_high=$ci_high,
    e.p_value=$p_value, e.n_total=$n_total, e.arm_sizes_json=$arm_sizes_json,
    e.model=$model, e.time_unit_ucum=$time_unit_ucum, e.spans_json=$spans_json,
    e.certainty=$certainty
WITH e
OPTIONAL MATCH (o:Outcome {loinc: $outcome_loinc})
WITH e, o
MATCH (d:Document {doc_id: $doc_id})
MERGE (d)-[:REPORTS]->(e)
FOREACH (_ IN CASE WHEN o IS NULL THEN [] ELSE [1] END |
  MERGE (e)-[:MEASURES]->(o)
)
MERGE (v:EvidenceVariable {id: $evvar_id})
MERGE (e)-[:DEFINES]->(v);
```

### 9.4.4 AE rows to nodes/edges

```cypher
MERGE (ae:AdverseEvent {pt_code: $meddra_pt})  // if code not present, use (pt)
ON CREATE SET ae.pt = $term
WITH ae
MATCH (s:Study {nct_id: $nct_id})
MERGE (s)-[r:HAS_AE]->(ae)
SET r.grade=$grade, r.count=$count, r.denom=$denom, r.serious=$serious, r.onset_days=$onset_days;
```

---

## 9.5 FHIR alignment & exporters

**Mapping summary:**

* `:EvidenceVariable` → FHIR `EvidenceVariable`

  * `population_json` ⇒ `characteristic` (codeableConcepts using SNOMED/MONDO/HPO)
  * `interventions_json`/`comparators_json` ⇒ `characteristic` w/ RxNorm/UNII
  * `outcomes_json` ⇒ `characteristic` w/ LOINC
* `:Evidence` → FHIR `Evidence`

  * `statistic` with `statisticType` (HR/RR/OR/MD/SMD), `value`, `ci`, `pValue`, `sampleSize`
  * `certainty` uses GRADE if available
* Provenance fields (`:ExtractionActivity`) → FHIR `Provenance`

**Exporter contract (pseudo):**

```ts
interface FhirExportRequest { nct_id?: string; doc_id?: string; }
interface FhirExportResponse { resources: FhirBundle; warnings: string[]; }
```

* Validate all **CodeableConcepts** against the Concept Lexicon.
* Enforce UCUM in `Evidence.statistic.attributeEstimate.unit`.

---

## 9.6 Identity resolution & code precedence

* **Deterministic keys:** `NCT`, `RxCUI`, `UNII`, `LOINC`, `MedDRA` are primary.
* **Conditions:** Prefer `MONDO` (disease), then `SNOMED`, then `ICD‑11`.
* **Conflicts:** Do **not** merge nodes with different primary codes; link via `:SAME_AS` only if a curated crosswalk asserts equivalence.

---

## 9.7 Governance & SHACL‑like checks (runtime)

Before write:

* **UCUM validator:** units present in `:Outcome.unit_ucum`, `:Evidence.time_unit_ucum`, `facet:dose.unit`.
* **Code presence:** If `:Evidence` references `outcome_loinc`, ensure `:Outcome{loinc}` exists (create if missing).
* **Span presence:** `spans_json` non‑empty and fits originating chunk length.

Failing records go to `kg_write_deadletter` with `{reason, payload_hash}`.

---

# 10) Extraction schemas (strict, span‑grounded) — implementation details

## 10.0 Principles

* **Span‑grounded**: every numeric/text claim carries one or more `evidence_spans`.
* **No inference**: missing in text ⇒ field absent.
* **Normal form**: numeric fields as numbers, units in **UCUM**, codes in agreed systems.
* **Versioned**: `$id` includes `v1`. Backward‑compatible changes require `v1.x` with `schema_hash`.

---

## 10.1 PICO (EvidenceVariable) schema — full JSON Schema

`/schemas/extractions/pico.v1.json`

```json
{
  "$id": "extractions.pico.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["population", "interventions", "outcomes", "evidence_spans"],
  "properties": {
    "population": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["text"],
        "properties": {
          "text": {"type": "string"},
          "codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}}
        }
      }
    },
    "interventions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "drug": {
            "type": "object",
            "properties": {
              "rxcui": {"type": "string"},
              "label": {"type": "string"},
              "unii": {"type": "string"}
            }
          },
          "procedure": {"type": "string"},
          "device_udi_di": {"type": "string"},
          "dose": {
            "type": "object",
            "properties": {
              "amount": {"type": ["number", "string"]},
              "unit": {"type": "string"},
              "route": {"type": "string"},
              "frequency_per_day": {"type": "number"},
              "duration_days": {"type": "number"}
            },
            "required": ["amount", "unit", "route"]
          }
        }
      }
    },
    "comparators": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "drug": {
            "type": "object",
            "properties": {
              "rxcui": {"type": "string"},
              "label": {"type": "string"}
            }
          },
          "procedure": {"type": "string"}
        }
      }
    },
    "outcomes": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["name"],
        "properties": {
          "name": {"type": "string"},
          "loinc": {"type": "string"},
          "codes": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Code"}}
        }
      }
    },
    "timeframe": {"type": "string"},
    "evidence_spans": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Span"}, "minItems": 1}
  },
  "additionalProperties": false
}
```

**Normalization rules:**

* If both brand and generic names appear, keep `drug.label` as **generic**; add brand to alternates only in free text if needed.
* Map ages (`“Adults 18–85 years”`) into a derived, non‑schema field `derived_logic.age={gte, lte}` for internal SHACL checks (not persisted in PICO JSON; persisted in Eligibility schema).

---

## 10.2 Effect measure (Evidence) schema — full JSON Schema

`/schemas/extractions/effects.v1.json`

```json
{
  "$id": "extractions.effects.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["type", "value", "evidence_spans"],
  "properties": {
    "type": {"type": "string", "enum": ["HR","RR","OR","MD","SMD"]},
    "value": {"type": "number"},
    "ci_low": {"type": "number"},
    "ci_high": {"type": "number"},
    "p_value": {"type": ["number","string"]},        // allow "p<0.001"
    "n_total": {"type": "integer", "minimum": 1},
    "arm_sizes": {
      "type": "object",
      "properties": {
        "int": {"type": "integer", "minimum": 1},
        "comp": {"type": "integer", "minimum": 1}
      }
    },
    "model": {"type": "string"},
    "outcome_loinc": {"type": "string"},
    "time_unit_ucum": {"type": "string"},
    "certainty": {"type": "string", "enum": ["high","moderate","low","very-low"]},
    "evidence_spans": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Span"}, "minItems": 1}
  },
  "additionalProperties": false
}
```

**Parsing guidance (agent):**

* Accept **either** “CI 95% 0.61–0.95” or “95% CI (0.61, 0.95)”.
* Reject negative values for `HR/RR/OR`. If negative detected, mark record invalid.

---

## 10.3 Adverse events schema — full JSON Schema

`/schemas/extractions/ae.v1.json`

```json
{
  "$id": "extractions.ae.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["term", "evidence_spans"],
  "properties": {
    "term": {"type": "string"},
    "meddra_pt": {"type": "string"},
    "grade": {"type": ["string","integer"], "pattern": "^[1-5]$"},
    "count": {"type": "integer", "minimum": 0},
    "denom": {"type": "integer", "minimum": 0},
    "arm": {"type": "string", "enum": ["intervention","comparator","placebo","overall","unspecified"]},
    "onset_days": {"type": "integer", "minimum": 0},
    "serious": {"type": "boolean"},
    "evidence_spans": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Span"}, "minItems": 1}
  },
  "additionalProperties": false
}
```

**Row extraction from tables:**

* Respect atomicity: one JSON per AE row per arm.
* If table is **% incidence** without denom, omit `denom` and keep `count` as `null` (omit per schema); do not back‑compute counts.

---

## 10.4 Eligibility schema — full JSON Schema

`/schemas/extractions/eligibility.v1.json`

```json
{
  "$id": "extractions.eligibility.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["type", "criteria", "evidence_spans"],
  "properties": {
    "type": {"type": "string", "enum": ["inclusion","exclusion"]},
    "criteria": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["text"],
        "properties": {
          "text": {"type": "string"},
          "logic": {
            "type": "object",
            "properties": {
              "age": {
                "type": "object",
                "properties": {"gte": {"type":"number"}, "lte": {"type":"number"}},
                "additionalProperties": false
              },
              "lab": {
                "type": "object",
                "required": ["loinc", "op", "value", "unit"],
                "properties": {
                  "loinc": {"type":"string"},
                  "op": {"type":"string", "enum":[">",">=","<","<=","="]},
                  "value": {"type":"number"},
                  "unit": {"type":"string"}      // UCUM
                }
              },
              "condition": {
                "type": "object",
                "properties": {
                  "mondo": {"type":"string"},
                  "snomed": {"type":"string"},
                  "icd11": {"type":"string"}
                }
              },
              "temporal": {
                "type": "object",
                "properties": {"op":{"type":"string","enum":[">",">=","<","<="]}, "days":{"type":"integer","minimum":0}}
              }
            },
            "additionalProperties": true
          }
        },
        "additionalProperties": false
      }
    },
    "evidence_spans": {"type": "array", "items": {"$ref": "facets.common.v1.json#/$defs/Span"}, "minItems": 1}
  },
  "additionalProperties": false
}
```

---

## 10.5 Extractor pipeline & validators

### 10.5.1 Orchestration

1. **Select chunks** by facet type or path heuristics:

   * PICO from Abstract, Methods, Registries
   * Effects from Results/Outcome tables
   * AE from AE tables/sections
   * Eligibility from ClinicalTrials.gov sections, SPL “Contraindications” not used for eligibility
2. **Run LLM extractor** with the appropriate prompt.
3. **Run normalizers** (units, codes).
4. **Validate JSON** against the schema. On failure:

   * Attempt auto‑repair (e.g., coerce `"3"`→`3` for grade).
   * If still invalid, dead‑letter with `schema_errors[]`.

### 10.5.2 SHACL/consistency checks (pre‑KG write)

* **UCUM check:** values & units consistent (e.g., `eGFR` in `mL/min/1.73m2`).
* **Effect sanity:** `HR/RR/OR > 0`; `ci_low ≤ value ≤ ci_high`.
* **AE completeness:** if `grade` present, ensure `1–5`.
* **Eligibility numeric:** `age.gte ≤ age.lte` when both present.

### 10.5.3 Provenance attach

All extractor outputs include **activity envelope**:

```json
{
  "activity": {
    "model": "qwen3-<variant>",
    "version": "x.y.z",
    "prompt_hash": "<sha256>",
    "schema_id": "extractions.effects.v1.json",
    "schema_hash": "<sha256>",
    "ts": "ISO8601"
  }
}
```

When writing to KG, create/merge `(:ExtractionActivity {id:<deterministic-hash>})` and add `:WAS_GENERATED_BY` edges.

---

## 10.6 From extraction → graph

**Mapping rules:**

* **PICO → :EvidenceVariable**

  * `population[*].codes` ⇒ connect via `:ABOUT` edges to `:Condition|:Phenotype`
  * `interventions[*].drug` ⇒ ensure `:Drug{rxcui}` exists; connect via `:USES_INTERVENTION`
  * `outcomes[*].loinc` ⇒ ensure/create `:Outcome{loinc}`
* **Effect → :Evidence**

  * Link to `:Outcome{loinc}` (if present) via `:MEASURES`
  * Link to corresponding `:EvidenceVariable` via `:DEFINES`
* **AE → :AdverseEvent**

  * Create `:AdverseEvent{pt_code}`; attach relationship attributes at edge
* **Eligibility → :EligibilityConstraint**

  * Store `logic_json` verbatim; connect `(:Study)-[:HAS_ELIGIBILITY]->(:EligibilityConstraint)`

---

## 10.7 Idempotency keys (for safe re‑runs)

* **PICO EV id:** `sha1(doc_id + chunk_id + normalized(population|interventions|outcomes|timeframe))`
* **Evidence id:** `sha1(doc_id + chunk_id + outcome_key + type + numeric_tuple)`
* **Eligibility id:** `sha1(doc_id + chunk_id + type + hash(criteria[]))`
* **AE row key:** `sha1(doc_id + chunk_id + meddra_pt + grade? + arm?)`

---

## 10.8 Error handling & review queues

* **Dead letters topics:**

  * `facet_gen_fail`: LLM JSON parse errors, token budget overflow
  * `extract_schema_fail`: schema validation failures
  * `kg_write_fail`: Neo4j constraint violations or code conflicts
* **Review UI fields:** show verbatim `quote`, highlight spans on PDF coordinates via `span_map`.

---

## 10.9 Examples (concise)

### 10.9.1 Facet → Evidence write (endpoint)

1. `facet:endpoint` (chunk) →
2. Normalize to `effects.v1.json` →
3. `MERGE` `:Outcome{loinc}` (if code) →
4. `MERGE` `:Evidence{id}` + `:ExtractionActivity` →
5. `(:Document)-[:REPORTS]->(:Evidence)-[:MEASURES]->(:Outcome)`

### 10.9.2 AE table row

1. Row “Hyperkalemia Grade 3: 12/250 (Drug), 4/248 (Placebo)”
2. Two `ae.v1.json` records →
3. `MERGE` `:AdverseEvent{pt_code:10020772}` →
4. `(:Study)-[:HAS_AE {grade:3,count:12,denom:250,arm:'intervention'}]->(:AdverseEvent)`
   +
   `(:Study)-[:HAS_AE {grade:3,count:4,denom:248,arm:'comparator'}]->(:AdverseEvent)`

---

## 10.10 Testing checklist (per schema)

* **PICO**

  * Mixed case drug names → RxCUI resolves
  * Multi‑arm trials → multiple interventions captured
  * Outcomes without codes allowed; coded when LOINC present

* **Effects**

  * Accept “95% CI 0.61–0.95” and “CI [0.61,0.95]”
  * Reject `HR=-0.2` (sanity)
  * Accept `p<0.001` (string)

* **AE**

  * Grade optional; if present must be 1–5
  * Denominator 0 allowed only if **explicit**; otherwise omit field

* **Eligibility**

  * Age/text both present → `logic.age` derived as numbers
  * Lab UCUM validated against LOINC

---

## 10.11 Performance & storage notes

* **Facet size cap:** Enforced by token budget; typical < 600 bytes/facet.
* **Neo4j property limits:** Large `text` on `:Chunk` is OK; store `spans_json` compressed (optional) if size > 4KB.
* **Throughput:** Run facet LLM with batching; typical 2–3 facets/chunk, ~20–40ms post‑processing overhead.
* **Reproducibility:** `prompt_hash` + `schema_hash` ensure deterministic audit; re‑runs with same inputs must produce identical ids (10.7).

---

## 10.12 APIs (agents call)

* `POST /facet/generate`
  **Body:** `{chunk_id}`
  **Out:** `{facet_types:[], facets:{pico?, endpoint?[], ae?[], dose?[]}, activity}`

* `POST /extract/{pico|effects|ae|eligibility}`
  **Body:** `{chunk_id, facet_payload?}`
  **Out:** `extractions.*.v1.json + activity`

* `POST /kg/write`
  **Body:** `{doc_id, extractions:[...], activity}`
  **Out:** `{written:{nodes, rels}, warnings:[]}`

> Each POST **must** reject payloads lacking `evidence_spans` or failing schema validation.

---

### TL;DR for agents

1. **Detect facets** per chunk → **generate** strict JSON (≤120 tokens) with spans.
2. **Normalize & code** (UCUM, RxCUI, LOINC, MedDRA); attach confidences; **validate**.
3. **Write** to Neo4j using **MERGE** patterns with **idempotency keys**; attach **ExtractionActivity** on every new `:Evidence`, `:EvidenceVariable`, `:EligibilityConstraint`.
4. **Index** facet JSON alongside chunk text in ES/OpenSearch and keep Qwen vectors on chunks.
5. **Fail closed**: no spans ⇒ no write. Log to dead‑letters with reason and payload hash.

This completes the exhaustive, implementation‑ready detailing for **Sections 8–10**.

Below is an **agent‑ready, engineering‑grade expansion** of **Sections 11 and 12**. It specifies algorithms, data contracts, scoring, filters, failure modes, and operational governance so autonomous agents can implement without further clarification.

---

# 11) Query & RAG flows (medical intents) — implementation details

## 11.0 Objective & guarantees

**Objective:** Given a user query (natural language and/or codes), return **span‑grounded medical evidence** by fusing **BM25F + SPLADE‑v3 + Qwen3 dense** over **Chunks + Facets** with clinical intent routing and ontology expansion. Responses are auditable (every claim points to `evidence_spans` in IR/Chunk).

**SLOs (default):**

* **P95 latency:** ≤ 1200 ms @ topK=20 (no reranker) / ≤ 2000 ms (with reranker top100→top25).
* **Recall@20:** ≥ target in §12 (dev set).
* **Determinism:** same inputs → same ordered hits (seeded ANN; frozen weights).

---

## 11.1 Intents, trigger lexicon & classifier

**Supported intents (v1.0‑med):**
`pico`, `endpoint`, `adverse_event`, `dose`, `eligibility`, `contraindication`, `biomarker_lab`, `guideline_strength`, `safety_signal`, `trial_design_phase`.

**Routing = rules + lightweight classifier.**

### 11.1.1 Deterministic triggers (first pass)

* **`endpoint`** if query contains any of `{HR, OR, RR, hazard ratio, odds ratio, risk ratio, risk difference, confidence interval, CI, p-value, efficacy, endpoint, outcome, mortality rate, hospitalization rate}`.
* **`adverse_event`** if any `{adverse, AE, toxicity, side effect, MedDRA, CTCAE, grade, SAE, safety}`.
* **`dose`** if any `{dose, dosing, dosage, mg, mcg, qd, bid, tid, q12h, infusion, route, oral, IV, subcutaneous, SC, intramuscular, IM}`.
* **`eligibility`** if any `{inclusion, exclusion, eligibility, criteria, age, BMI, eGFR, creatinine, LFTs, prior MI}`.
* **`biomarker_lab`** if any `{LOINC, biomarker, lab, assay, sensitivity, specificity, PPV, NPV, cut-off, threshold}`.
* **`guideline_strength`** if any `{recommendation, GRADE, strong, conditional, certainty}`.
* **`contraindication`** if any `{contraindication, warning, boxed warning, do not use with}`.
* **`trial_design_phase`** if any `{phase, randomization, blinded, crossover, parallel, allocation}`.
* Else **`pico`** by default.

### 11.1.2 ML classifier (second pass, tie‑break / multi‑intent)

* Linear SVM or Logistic regression over: character n‑grams, word n‑grams, clinical entity tags, code presence (RxCUI/LOINC/NCT), and **facet priors** learned from historical queries.
* Output `p(intent)` for each; accept:

  * Rules fire → keep.
  * Else top class with `p ≥ 0.55`; if none, choose `pico`.
* **Multi‑intent** allowed when `p(top2) ≥ 0.45` and intents are `{endpoint, adverse_event}` (common pair).

---

## 11.2 Query canonicalization & concept detection

**Normalization (pure, order‑preserving where possible):**

1. Lowercase except units/codes; normalize whitespace/punctuation; protect hyphenated drug names (e.g., “sacubitril/valsartan”).
2. Extract **deterministic IDs** via regex: `NCT\d+`, `PMID:\d+`, `LOINC:\S+`, `RxCUI:\d+`, `UNII:[A-Z0-9]+`, `ICD11:[A-Z0-9.]+`, `SNOMED:\d+`, **MedDRA PT code** (numbers).
3. **NER/dictionary:** scispaCy/QuickUMLS over query; for each span → candidate concepts (Section 7). Keep top concept id + synonyms.
4. **Abbreviation expansion:** HFrEF→“heart failure with reduced ejection fraction”; MI→“myocardial infarction”; CV→“cardiovascular”; DM→“diabetes mellitus”; eGFR; LVEF; ICU; etc.
5. **Units:** normalize to **UCUM** tokens (mg, mL/min/1.73m2, etc.).

**Output:** `QueryObject` (see next).

---

## 11.3 QueryObject (typed request to retrievers)

```json
{
  "q_raw": "does sacubitril/valsartan reduce CV mortality vs enalapril in HFrEF?",
  "intent": "endpoint",
  "must_terms": ["sacubitril/valsartan","enalapril","cardiovascular mortality"],
  "should_terms": ["HFrEF","NYHA","mortality","hazard ratio","95% CI"],
  "neg_terms": ["animal","in vitro"],
  "codes": { "RxCUI": ["12345","..."], "LOINC": [], "ICD11": [], "SNOMED": [] },
  "ids": { "NCT": [], "PMID": [] },
  "filters": {
    "doc_types": ["imrad","registry","spl","guideline"],   // optional
    "year_from": 2000, "year_to": 2025,
    "ae_grade_min": null, "phase": null,
    "language": ["en"]
  },
  "boosts": { "facet_type": ["endpoint"], "title_path": 2.0, "facet_json": 1.6 },
  "topK": 200, "rerank_topN": 100
}
```

* **Population synonyms**: expand `must/should_terms` using Concept Lexicon (Section 5) with **de‑dup**, cap ≤ 20 tokens.
* **Safety:** Strip PII patterns (emails, phone numbers) if user appended them accidentally (log but ignore).

---

## 11.4 Retriever specifics

### 11.4.1 BM25F over OpenSearch/ES

* **Indexed fields:** `body, title_path, facet_json, table_lines`.
* **Boosts:** `title_path:2.0`, `facet_json:1.6`, `table_lines:1.2`, `body:1.0` (default); per‑intent adjustments below.
* **Analyzer:** english + medical stopwords list (retain **negations** like “no”, “not”).
* **Query template (OpenSearch)**:

```json
{
  "query": {
    "bool": {
      "must": [{"simple_query_string": {"query": "<must_terms>", "fields": ["body^1.0","title_path^2.0","facet_json^1.6","table_lines^1.2"], "default_operator": "and"}}],
      "should": [{"multi_match": {"query": "<should_terms>", "fields": ["body","facet_json^1.6","title_path^2.0"]}}],
      "must_not": [{"terms": {"body": ["<neg_terms>"]}}],
      "filter": [
        {"terms": {"facet_type": ["<intent-mapped-facets>"]}},   // optional
        {"range": {"year": {"gte": <from>, "lte": <to>}}},
        {"terms": {"language": ["en"]}}
      ]
    }
  },
  "size": <topK_bm25>,
  "_source": ["chunk_id","doc_id","facet_*","path","score_fields"]
}
```

**Per‑intent facet filter defaults:**

* `endpoint` → `facet:endpoint`
* `adverse_event` → `facet:ae`
* `dose` → `facet:dose`
* `eligibility` → (internal) `facet:eligibility`
* `pico` → no facet filter (full text + `facet:pico` both)

### 11.4.2 SPLADE‑v3 (sparse neural)

* **Doc‑side:** precomputed expanded term vectors per chunk+facets (offline).
* **Query‑side:** runtime expansion; topK per index (same `topK_splade` as BM25).
* **API:** same as BM25 endpoint with custom similarity plugin or via **vector of term weights** if deployed separately.
* **Intent weights:** emphasize numeric measure tokens for `endpoint` (e.g., “HR”, “CI”, numerics).

### 11.4.3 Dense (Qwen3‑Embedding‑8B)

* **ANN index:** FAISS HNSW or Neo4j native vector (cosine), dim=4096.
* **Query vector:** embed **(canonical_query + facet hints)**:

  * Build `query_text_dense`:

    * `endpoint`: “Outcome/effect size focus. {q_raw}. Include metrics like HR/RR/OR and confidence intervals.”
    * `adverse_event`: “Adverse events, MedDRA terms, grades. {q_raw}.”
    * others analogous.
* **Filters:** post‑ANN filtering by metadata (intent→facet type, year, language).

**TopK per retriever (defaults):** `bm25=200, splade=200, dense=200`.

---

## 11.5 Score fusion

**Inputs:** Three lists of `(chunk_id, score_bm25 | score_splade | score_dense)`

**Normalization:** per‑retriever min‑max over the union of its topK (robust to outliers via 5th/95th percentile clipping).

```
score_norm = (score - p5) / (p95 - p5); clamp to [0,1]
```

**Fusion (default):**

```
Fused = 0.5*SPLADE_norm + 0.35*DENSE_norm + 0.15*BM25_norm
```

**Fallback:** Reciprocal Rank Fusion (RRF) with `k=60` if fewer than 10 items overlap:

```
RRF = Σ_r (1 / (k + rank_r))
```

**Calibrations:** maintain per‑intent fusion weights (override allowed by config).

---

## 11.6 Re‑ranking (optional but on by default)

* **Model:** Qwen3 cross‑encoder reranker.
* **Input:** top `rerank_topN` fused candidates with **query text + candidate snippet** (first 512 tokens of chunk, plus `facet_json` if present).
* **Output:** `rerank_score ∈ ℝ`; final ordering by rerank_score.
* **Budget:** `rerank_topN=100` → return top 25.

**Safety constraint:** If reranker demotes items with **deterministic ID match** (NCT, PMID, RxCUI mentioned in query), protect at least rank‑10 (never drop below the top‑10).

---

## 11.7 Neighbor merge (passage assembly)

**When:** prior to answer generation to improve context continuity.

**Algorithm:**

1. For each selected chunk, fetch **adjacent chunks** from same `doc_id` where `abs(chunk.start - selected.end) ≤ window_chars` (default 1200) or same `path` parent.
2. **Eligibility to merge:** (a) same section/`path` root, (b) cosine(Qwen embedding) ≥ `0.60`, (c) no table boundaries in between (unless intent `endpoint` and both are within Results).
3. Build **passage** with at most 3000 tokens (truncate tail).
4. Carry forward a **span remap** table from each original chunk.

---

## 11.8 Intent‑specific pipelines

### 11.8.1 `endpoint`

* **Facet filter:** `facet:endpoint` preferred.
* **Boost fields:** increase `facet_json` to 2.0; `table_lines` 1.5.
* **Dense hints:** inject “95% CI”, “p value”, “sample size”.
* **Post‑retrieval extractor:** run **effects.v1** extractor on top‑N passages; keep only valid (`HR/RR/OR/MD/SMD`, CI sanity).
* **Aggregation:** group by `(outcome_loinc|normalized_outcome_name, type)`; keep best evidence (lowest p or highest quality if GRADE available).

### 11.8.2 `adverse_event`

* **Facet filter:** `facet:ae`.
* **AE schema:** run **ae.v1** extractor to convert textual/table evidence into normalized rows per arm.
* **Filters:** optional `grade ≥ g` (user filter); default include all.
* **Aggregation:** collapse same MedDRA PT across documents with `meta:{nct_id, spl_setid}` preserved.

### 11.8.3 `dose`

* **Facet filter:** `facet:dose` or SPL LOINC section `34066-1`.
* **Normalizer:** UCUM unit harmonizer; resolve RxCUI; dedupe by `(rxcui, route, frequency)`.

### 11.8.4 `eligibility`

* **Sources:** ClinicalTrials.gov Eligibility; guidelines sometimes.
* **Extractor:** **eligibility.v1**; render criteria as structured logic; allow facet‐only retrieval.

### 11.8.5 `pico`

* **Goal:** contextual PICO for downstream question rewrite.
* **Facet filter:** prefer `facet:pico` when present else full text.

### 11.8.6 `biomarker_lab`

* **Facet bias:** tables with lab cutoffs; boost LOINC codes; apply unit harmonization; prefer chunks with numeric thresholds.

### 11.8.7 `guideline_strength`

* **Scope:** guideline documents; parse GRADE terms; extract as `Evidence.certainty`.

### 11.8.8 `contraindication` / `safety_signal`

* **Sources:** SPL Warnings/Contraindications and AE sections; post‑hoc join with AE incidence across multiple studies (see §11.10 multi‑hop).

---

## 11.9 Answerer (LLM) & grounding contract

**Contract:** Always return **span‑grounded** JSON and a short natural‑language summary **only** from retrieved passages.

**Answer JSON (generic):**

```json
{
  "intent": "endpoint",
  "answers": [
    {
      "doc_id": "...",
      "chunk_id": "...",
      "nct_id": "NCT...",
      "pmid": "123456",
      "effect": {"type":"HR","value":0.76,"ci_low":0.61,"ci_high":0.95,"p_value":"0.012"},
      "outcome": {"name":"CV mortality","loinc":"..."},
      "population": "Adults with HFrEF (NYHA II–III)",
      "intervention": "sacubitril/valsartan",
      "comparator": "enalapril",
      "evidence_spans": [{"start":123,"end":167,"quote":"..."}, {"start":...}],
      "provenance": {"doc_uri":"...","page":7}
    }
  ],
  "warnings": []
}
```

**Guardrails:**

* If **no spans**, **no answer** (return `"answers":[],"warnings":["no span‑grounded evidence"]`).
* For **conflicting evidence**, return multiple entries with notes (do not synthesize meta‑analysis).

---

## 11.10 KG‑assisted multi‑hop (optional for complex queries)

Use Neo4j to **join** across entities:

* **Example:** “Are there Grade ≥3 hyperkalemia signals with sacubitril/valsartan?”

  1. Resolve drug → `:Drug{rxcui}`.
  2. Traverse `(:Study)-[:HAS_ARM]->(:Arm)-[:USES_INTERVENTION]->(:Drug)` then to AEs:

     ```
     MATCH (d:Drug{rxcui:$rxcui})<-[:USES_INTERVENTION]-(:Arm)<-[:HAS_ARM]-(s:Study)
           -[r:HAS_AE]->(ae:AdverseEvent {pt:'Hyperkalemia'})
     WHERE coalesce(r.grade,0) >= 3
     RETURN s.nct_id, r.count, r.denom
     ```

  3. Rank by incidence or count, fetch supporting `:Chunk` via `(:Document)-[:REPORTS]->(:Evidence)` or `(:Document)-[:HAS_CHUNK]->(:Chunk)` with **MENTIONS** edges.

**When to enable:** if intent `safety_signal` or if text query returns < 5 hits.

---

## 11.11 Filters & query params (API)

**`POST /search`**

```json
{
  "q": "hyperkalemia with sacubitril/valsartan",
  "intent": "adverse_event",
  "filters": {
    "grade_min": 3,
    "doc_types": ["imrad","spl","registry"],
    "year_from": 2010,
    "codes": {"RxCUI":["12345"], "MedDRA":["10020772"]},
    "nct": []
  },
  "topK": 20,
  "reranker": true
}
```

**Response:** `hits[]` with `{chunk_id, doc_id, doc_meta, score, fused_components, spans, facet_payload, rerank_score?}` + `answer_json` if `generate=true`.

---

## 11.12 Caching & de‑duplication

* **Query cache key:** `sha1(intent | canonical_query | filters | version)`.
* **TTL:** 10 minutes (short) / 24 hours (saved searches).
* Deduplicate hits **per doc** by keeping best‑scoring chunk; keep both if they represent **different facets** (e.g., `endpoint` and `ae`).

---

## 11.13 Error handling

* If any retriever fails, **degrade gracefully**: fuse remaining; annotate `warnings`.
* If reranker times out, return fused list.
* If concept resolver fails, skip code expansion (log).

---

## 11.14 Configuration (extends §14)

```yaml
search:
  ann:
    index: "faiss-hnsw"
    hnsw: {M: 32, efSearch: 128, efConstruction: 200}
  bm25:
    fields: ["body","title_path","facet_json","table_lines"]
    boosts: {title_path: 2.0, facet_json: 1.6, table_lines: 1.2, body: 1.0}
  splade:
    model: "naver/splade-v3"
    topK: 200
  dense:
    model: "qwen3-embedding-8b"
    topK: 200
  fusion:
    method: "weighted"        # or "rrf"
    weights: {splade: 0.5, dense: 0.35, bm25: 0.15}
    rrf_k: 60
  reranker:
    enabled: true
    model: "qwen3-rerank"
    topN: 100
  neighbor_merge:
    window_chars: 1200
    max_tokens: 3000
    min_cosine: 0.60
  safety:
    protect_deterministic_ids_topN: 10
```

---

# 12) Quality, evaluation & governance (medicine) — implementation details

## 12.0 Goals

* Quantify and continuously improve **chunking, retrieval, EL, extraction**, and **end‑to‑end** answer quality.
* Enforce **licensing, privacy, and medical safety** constraints.
* Provide **observable** operations with **review workflows** and **drift detection**.

---

## 12.1 Datasets & splits

**Doc families (target counts, open sources where licensing permits):**

* **IMRaD papers (PMC OA)**: 3,000 train / 1,000 dev / 1,000 test.
* **ClinicalTrials.gov**: 2,000 train / 700 dev / 700 test (Eligibility/Outcome).
* **SPL labels (DailyMed)**: 1,000 train / 300 dev / 300 test.
* **Guidelines**: 300 train / 100 dev / 100 test (where redistribution allowed).

**Query sets (paired with gold):**

* **Endpoint queries** (n≈600): “HR/RR/OR for {outcome} with {drug} in {population}”.
* **AE queries** (n≈500): “Grade ≥3 {PT} with {drug}”.
* **Dose queries** (n≈400): “Recommended {drug} {route} dosing in {population}”.
* **Eligibility queries** (n≈400): “Inclusion criteria age range for NCT… / for {condition} trials”.
* **PICO/context** (n≈400).

**Gold annotations:**

* **Gold spans** (char offsets) for answers.
* **Gold codes** (LOINC, MedDRA PT, RxCUI, MONDO/SNOMED).
* **Numeric gold** for effect sizes with tolerances.

---

## 12.2 Metrics & definitions

### 12.2.1 Retrieval

* **Recall@K**: fraction of queries with at least one **gold‑containing chunk** in top‑K (K=5,10,20).
* **nDCG@K**: graded relevance (2=exact gold span in chunk; 1=has correct section but not span; 0 otherwise).
* **MRR**: reciprocal rank of first gold hit.

### 12.2.2 Chunking

* **Intra‑coherence**: median pairwise cosine (Qwen embeddings) per chunk; target ≥ 0.60 narrative / 0.50 bullets.
* **Boundary alignment**: % of true boundaries not split, by family (IMRaD/registry/SPL/guideline). Target ≥ 65%.
* **Table integrity**: no split rows (0 tolerance).

### 12.2.3 Entity Linking (EL)

* **ID accuracy (deterministic)**: exact match rate for `RxCUI/UNII/NCT/UDI` from text → code; target ≥ 0.90.
* **Concept EL accuracy**: micro‑avg accuracy vs. gold UMLS/SNOMED/LOINC; target ≥ 0.85.
* **Confidence calibration**: reliability diagram ECE ≤ 0.05 at accept threshold 0.70.

### 12.2.4 Extraction

* **PICO completeness**: fraction of queries where all `{population, interventions, outcomes}` are present and non‑empty; target ≥ 0.85.
* **Effect size F1**:

  * **Exact**: numeric triple `(type, value, ci_low, ci_high)` exact.
  * **Relaxed**: tolerate rounding (abs err ≤ 0.01) and p‑value formats; report both.
  * Target ≥ 0.80 (relaxed).
* **AE mapping**: accuracy of (PT + grade) vs. gold; target ≥ 0.80.
* **Eligibility logic accuracy**: correct normalization of age ranges and at least one lab threshold per trial (where present): ≥ 0.85.

### 12.2.5 End‑to‑end (RAG)

* **Faithfulness (span‑grounding rate)**: % of answer claims with at least one valid evidence span. **Target 100%** (hard requirement).
* **Hallucination rate**: % answers with claims not supported by any retrieved span. Target ≤ 1%.
* **Answer utility (human eval)**: 3‑point Likert (0 unusable / 1 partially / 2 directly actionable). Target avg ≥ 1.6.

### 12.2.6 Latency & resource

* **P50/P95/P99 latency** under standard load.
* **GPU/CPU utilization**; memory watermark; index QPS headroom ≥ 30%.

---

## 12.3 Evaluation harness & automation

**Structure:**

* Repo `eval/` with:

  * `eval_retrieval.py` — computes Recall/nDCG/MRR for each retriever and fusion.
  * `eval_chunking.py` — computes coherence and boundary metrics against annotated boundaries.
  * `eval_el.py` — computes EL accuracy & calibration.
  * `eval_extract.py` — computes PICO completeness, effect F1, AE accuracy, eligibility logic.
  * `eval_rag.py` — end‑to‑end metrics, faithfulness checks, hallucination detection.

**Data interfaces:** JSONL of `{qid, query, intent, filters?, gold_doc_ids?, gold_spans[]?, gold_codes[]?}`.

**CI gating:** PRs that modify chunker, retrievers, EL, extractors must run the harness and **pass thresholds** defined in §12.12.

---

## 12.4 Error analysis & dashboards

* **Dashboards (Grafana/ELK):**

  * Retrieval overlap Venn (BM25/SPLADE/Dense).
  * Query class distribution over time.
  * Dead‑letter topics counts & reasons (§10.8).
  * Latency histograms (by intent & stage).
  * Drift indicators (§12.8).

* **Explain tooling:**

  * Show **term contributions** for SPLADE (top expanded terms).
  * Show **pairwise cosine** for neighbor merges (why passages were merged).
  * Show **reranker** feature attribution (if supported).

---

## 12.5 SHACL & schema validation (KG guard)

Define **SHACL shapes** to validate key graph invariants before/after writes.

* **UCUM units shape:** `:Outcome.unit_ucum`, `:Evidence.time_unit_ucum`, `facet:dose.unit` ∈ accepted UCUM code set.
* **Code presence shape:** If `:Evidence.outcome_loinc` exists → `(:Evidence)-[:MEASURES]->(:Outcome{loinc})` must exist.
* **AE edge shape:** `(:Study)-[:HAS_AE]->(:AdverseEvent)` must have `count≥0`, `denom≥0` (if present), and `grade∈{1..5}` (if present).
* **Provenance shape:** Any of `:Evidence|:EvidenceVariable|:EligibilityConstraint` must have **at least one** `:WAS_GENERATED_BY` with `model`, `version`, `schema_hash`, `ts`.

**Execution:** Run SHACL validator on batches; **block** commit on violations, route to `kg_write_deadletter`.

---

## 12.6 Governance: licensing & ACLs

* **Vocabulary ACLs:**

  * **MedDRA** and **SNOMED CT (outside member countries)**: require license flag on deployment. Gate features:

    * **If not licensed:** do **not** ship MedDRA PT codes (store textual AE terms only) and do **not** resolve SNOMED; provide clear warnings in logs and surface `"code_redacted": true` in outputs.
  * UMLS: log acceptance version; restrict downstream exposure per source terms.

* **Source usage rules:**

  * **PMC OA** only for full‑text bulk; non‑OA PubMed abstracts ok per E‑utilities.
  * **DailyMed SPL** & **GUDID**: public.

* **Enforcement:** policy module reads `policy.yaml` (below) and **denies** KG writes violating license.

```yaml
policy:
  vocabs:
    SNOMED: {licensed: true, territory: "US"}
    MedDRA: {licensed: false}
    LOINC: {licensed: true}
    RxNorm: {licensed: true}
    HPO: {licensed: true}
  actions:
    redact_unlicensed_codes: true
    block_kg_write_without_provenance: true
```

---

## 12.7 Privacy & PHI handling

* **Default corpus** excludes PHI (no EHR notes). If EHR later added:

  * Run **de‑identification** pipeline (name/ID/date shift).
  * Store PHI‑bearing text **outside** search index; instead index PHI‑free projections.
  * Audit logging for every PHI document access; role‑based access with **least privilege**.
* **Query sanitization:** Strip user‑supplied PII tokens in `q_raw` prior to logging.

---

## 12.8 Drift detection & recalibration

* **Retriever drift:** track distribution of fused scores and overlap rates weekly. Alert if:

  * Overlap (Jaccard) of top‑20 between this week vs last week < 0.6 for stable query set.
  * nDCG@10 drops > 3 points on sentinel queries.

* **EL drift:** monthly monitor concept popularity and acceptance rates; if accept rate < 80% or review queue backlog > threshold, lower `accept_threshold` by 0.02 or retrain.

* **Extraction drift:** numeric outlier detector:

  * For effect sizes, alert if `|median(HR) − historical_median| > 0.2` for same outcome/drug/population across new docs (possible parsing issue).

---

## 12.9 Human review workflows

* **Queues:**

  * `el_review`: unresolved EL (score < 0.70) or conflicts.
  * `extract_review`: schema‑invalid after auto‑repair.
  * `kg_conflict`: uniqueness constraint collisions.

* **Reviewer UI (requirements):**

  * PDF rendering with **span highlights** (use `span_map`).
  * One‑click **accept/correct/reject**; corrections create curated cross‑walks (`:SAME_AS` edges).
  * Provenance summary (model, version, prompt hash).

* **SLA:** 5 business days to clear critical items (affects safety_signal, contraindication).

---

## 12.10 Load & performance testing

* **Scenarios:**

  * Burst: 50 QPS for 2 min; steady: 10 QPS for 1 hour.
  * Mixed intents: endpoint 40%, AE 25%, dose 15%, eligibility 10%, others 10%.

* **Targets:** see §11.0 SLOs.

* **Artifacts:** flamegraphs per stage (BM25, SPLADE, ANN, reranker).

* **Back‑pressure:** If P95 > SLO for 3 windows:

  * Disable reranker temporarily.
  * Reduce `topK` to 100 for BM25/SPLADE and 100 for dense.
  * Switch fusion to RRF (cheaper).

---

## 12.11 Security & reliability

* **Secrets:** KMS‑backed; no secrets in logs.
* **Data at rest:** object store + Neo4j volumes encrypted.
* **Data in transit:** TLS everywhere.
* **Backups:** nightly KG and index snapshots; 14‑day retention.
* **Idempotency:** all write APIs accept `request_id`; dedupe on `(request_id, payload_hash)`.

---

## 12.12 CI/CD gates & acceptance thresholds (hard fails)

A PR cannot merge unless all below pass on **dev split**:

| Component          | Metric/Check                    | Threshold (min) |
| ------------------ | ------------------------------- | --------------- |
| Chunker            | Boundary alignment (per family) | ≥ 65%           |
| Retrieval (fusion) | nDCG@10 (overall)               | ≥ baseline +5   |
| Retrieval (fusion) | Recall@20 (each family)         | ≥ baseline +3%  |
| EL (IDs)           | Accuracy (RxCUI/UNII/NCT/UDI)   | ≥ 0.90          |
| EL (concepts)      | Accuracy (SNOMED/LOINC etc.)    | ≥ 0.85          |
| Extraction Effects | F1 (relaxed)                    | ≥ 0.80          |
| AE mapping         | Accuracy (PT + grade)           | ≥ 0.80          |
| Faithfulness       | Span‑grounding rate             | 100%            |
| SHACL              | Violations                      | 0               |
| Latency            | P95 (no reranker / reranker on) | ≤ 1200 / 2000ms |

If any licensing flag in `policy.yaml` changes to **false** for a previously used vocabulary, the CI must verify that **no tests** rely on those codes; otherwise **fail** with message “licensed vocab dependency detected”.

---

## 12.13 Reporting & audit artifacts

* **Monthly report** (auto‑generated PDF/HTML):

  * Retrieval metrics trends by intent.
  * Top failed queries with reasons (no spans; schema violations).
  * License compliance summary (vocabulary usage counts).
  * Data sources ingestion volume and failure rates.
* **Provenance snapshot:** list of **ExtractionActivity** versions seen that month with counts; highlight any with outlier error rates.

---

## 12.14 Ops runbooks (selected)

**Incident: “High hallucination rate”**

1. Verify span extraction step running; check logs for “no spans” warnings.
2. Ensure answerer uses passages with `spans_json` present.
3. If reranker on, sample demoted items → see if demotion removed span‑bearing chunks. Temporarily **disable reranker**, re‑run.

**Incident: “SPLADE index drift”**

1. Compare top‑terms distribution against last snapshot.
2. If mismatch, re‑run offline expansion with fixed seed and **freeze** vocabulary.
3. Reindex; run eval harness; flip traffic gradually.

**Incident: “MedDRA codes missing (license expired)”**

1. Confirm `policy.yaml` shows `MedDRA: licensed: false`.
2. Ensure `redact_unlicensed_codes` true.
3. Clear **facet:ae** code fields; retain textual PTs; run regression eval (AE accuracy will be measured w.r.t. text).

---

## 12.15 Example: end‑to‑end test spec (endpoint intent)

**Input query:** “Does sacubitril/valsartan reduce cardiovascular mortality vs enalapril in HFrEF?”

**Expected path:**

1. Intent→`endpoint`; resolve drugs (RxCUI), condition terms (HFrEF synonyms).
2. BM25/SPLADE/DENSE run with per‑intent boosts & facet filter (`endpoint`).
3. Fuse & rerank; neighbor‑merge passages.
4. Effects extractor returns HR and CI with spans.
5. Answerer returns **span‑grounded** JSON + succinct textual summary.
6. Metrics: hit must include gold trial doc id; effect numeric within ±0.01.

---

## 12.16 Extended config stanzas

```yaml
eval:
  splits: ["train","dev","test"]
  k_values: [5,10,20]
  relaxed_numeric_tolerance: 0.01
  hallucination:
    require_spans: true
    max_rate: 0.01
drift:
  sentinel_queries:
    file: "eval/sentinels.jsonl"
  weekly_overlap_jaccard_min: 0.6
observability:
  logs:
    pii_scrub: true
    sample_rate: 0.1
  metrics:
    push_interval_sec: 10
    sinks: ["prometheus","elasticsearch"]
```

---

### TL;DR for agents

1. **Route** queries to intents via rules + classifier; **expand** with ontology synonyms/codes.
2. **Retrieve in parallel**: BM25F, SPLADE‑v3, Qwen dense → **fuse** → optional **rerank**.
3. **Assemble passages** (neighbor merge), then **extract** per intent (effects/AE/dose/eligibility).
4. **Return** span‑grounded answers; **write** to KG if requested.
5. **Continuously evaluate** with the harness; enforce **SHACL**, **licensing ACLs**, **privacy**, and **SLOs**.

# 13) APIs (production‑grade, medicine‑tuned)

## 13.0 API surface, versioning, and conventions

* **Base URL:** `https://api.<org>.medkg/v1`
* **Versioning:** `v1` in path; **semantic versions** returned via `X-API-Version` header (e.g., `1.2.3`).
* **Content types:** requests **JSON** (`application/json`), streaming progress **SSE** (`text/event-stream`), bulk artifacts **NDJSON** (`application/x-ndjson`), uploads **multipart/form-data**.
* **Auth:** OAuth2 (client credentials or JWT bearer) **and** API key fallback for internal jobs.

  * **Scopes**: `ingest:read`, `ingest:write`, `chunk:write`, `embed:write`, `retrieve:read`, `map:write`, `extract:write`, `kg:write`, `catalog:read`, `admin:*`.
* **Idempotency:** header `Idempotency-Key` (UUIDv4). Server **must** return the same result for identical body+key for **24h**; store hash.
* **Tracing:** propagate `traceparent` (W3C), `x-request-id` (UUIDv4); log correlation everywhere.
* **Errors:** unified envelope:

  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR|LICENSE_DENIED|NOT_FOUND|RETRYABLE|UPSTREAM_TIMEOUT|INTERNAL",
      "message": "Human-readable summary",
      "details": [{"field":"...", "issue":"..."}],
      "retriable": true,
      "reference": "support doc or runbook URL"
    }
  }
  ```

* **Rate limits:** default `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.
* **Licensing enforcement:** header `X-License-Tier: internal|member|affiliate|public`. Server filters SNOMED/MedDRA/UMLS text based on caller; always returns **IDs**; may redact **labels/definitions** if unlicensed.

---

## 13.1 OpenAPI 3.1 (abridged but complete semantics)

> **Note:** The following YAML is directly loadable by tooling. Omitted schemas are provided below or referenced by `$ref`.

```yaml
openapi: 3.1.0
info:
  title: MedKG Ingest/Retrieval API
  version: 1.0.0
servers:
  - url: https://api.<org>.medkg/v1
security:
  - OAuth2: [ ]
  - ApiKeyAuth: [ ]
paths:
  /health:
    get:
      summary: Liveness/readiness probe
      operationId: getHealth
      responses:
        '200': { description: OK }
  /version:
    get:
      summary: Component and model versions
      operationId: getVersion
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: { $ref: '#/components/schemas/VersionInfo' }

  /ingest/clinicaltrials:
    post:
      summary: Pull ClinicalTrials.gov by NCT and write IR
      operationId: ingestClinicalTrials
      security:
        - OAuth2: [ "ingest:write" ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/IngestClinicalTrialsRequest' }
      responses:
        '200':
          description: Ingested
          content: { application/json: { schema: { $ref: '#/components/schemas/IngestResponse' } } }
        '207':
          description: Partial success with per-NCT status
          content: { application/json: { schema: { $ref: '#/components/schemas/IngestBatchResponse' } } }
        '4XX':
          description: Error
          content: { application/json: { schema: { $ref: '#/components/schemas/Error' } } }

  /ingest/dailymed:
    post:
      summary: Download SPL by setid/ndc and write IR with LOINC sections
      operationId: ingestDailyMed
      security: [ { OAuth2: [ "ingest:write" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/IngestDailyMedRequest' }
      responses:
        '200': { description: Ingested, content: { application/json: { schema: { $ref: '#/components/schemas/IngestResponse' } } } }
        '4XX': { description: Error, content: { application/json: { schema: { $ref: '#/components/schemas/Error' } } } }

  /ingest/pmc:
    post:
      summary: Fetch PMC OA XML by PMCID, convert to IR (IMRaD)
      operationId: ingestPMC
      security: [ { OAuth2: [ "ingest:write" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/IngestPMCRequest' }
      responses:
        '200': { description: Ingested, content: { application/json: { schema: { $ref: '#/components/schemas/IngestResponse' } } } }

  /chunk:
    post:
      summary: Run semantic chunker on IR Document(s)
      operationId: chunkDocuments
      security: [ { OAuth2: [ "chunk:write" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ChunkRequest' }
      responses:
        '200': { description: Chunked, content: { application/json: { schema: { $ref: '#/components/schemas/ChunkResponse' } } } }

  /embed:
    post:
      summary: Compute SPLADE terms + Qwen embeddings for Chunks/Facets/Concepts
      operationId: embedObjects
      security: [ { OAuth2: [ "embed:write" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/EmbedRequest' }
      responses:
        '200': { description: Embedded, content: { application/json: { schema: { $ref: '#/components/schemas/EmbedResponse' } } } }

  /retrieve:
    post:
      summary: Multi-retriever fusion; return top-N chunks with spans
      operationId: retrieve
      security: [ { OAuth2: [ "retrieve:read" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/RetrieveRequest' }
      responses:
        '200': { description: Results, content: { application/json: { schema: { $ref: '#/components/schemas/RetrieveResponse' } } } }

  /map/el:
    post:
      summary: Entity Linking adjudication
      operationId: mapEntityLinking
      security: [ { OAuth2: [ "map:write" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ELRequest' }
      responses:
        '200': { description: Mappings, content: { application/json: { schema: { $ref: '#/components/schemas/ELResponse' } } } }

  /extract/{kind}:
    post:
      summary: Span-grounded extraction
      operationId: extractKind
      security: [ { OAuth2: [ "extract:write" ] } ]
      parameters:
        - in: path
          name: kind
          required: true
          schema: { type: string, enum: [ pico, effects, ae, dose, eligibility ] }
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ExtractRequest' }
      responses:
        '200': { description: Extracted, content: { application/json: { schema: { $ref: '#/components/schemas/ExtractResponse' } } } }

  /kg/write:
    post:
      summary: Write nodes/edges to Neo4j with provenance
      operationId: writeKG
      security: [ { OAuth2: [ "kg:write" ] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/KGWriteRequest' }
      responses:
        '200': { description: Upserted, content: { application/json: { schema: { $ref: '#/components/schemas/KGWriteResponse' } } } }

components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: https://auth.<org>/oauth2/token
          scopes:
            ingest:write: Ingest sources
            retrieve:read: Search
            map:write: Concept mapping
            extract:write: Clinical extraction
            kg:write: Graph writes
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
  schemas:
    VersionInfo:
      type: object
      properties:
        apiVersion: { type: string }
        models:
          type: object
          additionalProperties: { type: string }  # e.g., qwen3-embedding: 1.0.2
        indices:
          type: object
          additionalProperties: { type: string }  # chunks_v1: hash
    IngestClinicalTrialsRequest:
      type: object
      required: [ nct_ids ]
      properties:
        nct_ids: { type: array, items: { type: string, pattern: "^NCT\\d{8}$" }, minItems: 1, maxItems: 200 }
        include_results: { type: boolean, default: true }
        fhir_view: { type: boolean, default: false }
        dedupe: { type: boolean, default: true }
        sync: { type: boolean, default: true }
    IngestDailyMedRequest:
      type: object
      properties:
        setids: { type: array, items: { type: string }, minItems: 1 }
        ndcs:   { type: array, items: { type: string }, minItems: 1 }
        sections: { type: array, items: { type: string }, description: "LOINC-coded sections to retain" }
        sync: { type: boolean, default: true }
      oneOf:
        - required: [ setids ]
        - required: [ ndcs ]
    IngestPMCRequest:
      type: object
      required: [ pmcids ]
      properties:
        pmcids: { type: array, items: { type: string, pattern: "^PMC\\d+$" }, minItems: 1, maxItems: 200 }
        oa_only: { type: boolean, default: true }
        sync: { type: boolean, default: true }
    IngestResponse:
      type: object
      properties:
        status: { type: string, enum: [ ok, queued ] }
        doc_ids: { type: array, items: { type: string } }
        objects_uri: { type: string, description: "s3://... of IR NDJSON" }
    IngestBatchResponse:
      type: object
      properties:
        results:
          type: array
          items:
            type: object
            properties:
              key: { type: string }     # NCT or setid/pmcid
              status: { type: string, enum: [ ok, not_found, error ] }
              doc_id: { type: string, nullable: true }
              error:  { $ref: '#/components/schemas/Error' }
    ChunkRequest:
      type: object
      required: [ doc_ids ]
      properties:
        doc_ids: { type: array, items: { type: string }, minItems: 1, maxItems: 200 }
        profile: { type: string, enum: [ imrad, registry, spl, guideline ], default: imrad }
        overlap: { type: number, minimum: 0, maximum: 0.5 }
        target_tokens: { type: integer, minimum: 100, maximum: 1200 }
        produce_facets: { type: boolean, default: true }
        persist: { type: boolean, default: true }
    ChunkResponse:
      type: object
      properties:
        chunks: { type: array, items: { $ref: '#/components/schemas/Chunk' } }
        facets: { type: array, items: { $ref: '#/components/schemas/Facet' } }
    Chunk:
      type: object
      required: [ chunk_id, doc_id, body, start_char, end_char ]
      properties:
        chunk_id: { type: string }
        doc_id: { type: string }
        title_path: { type: string }
        body: { type: string }
        start_char: { type: integer }
        end_char: { type: integer }
        meta: { type: object, additionalProperties: true }
    Facet:
      type: object
      properties:
        kind: { type: string, enum: [ pico, endpoint, ae, dose ] }
        chunk_id: { type: string }
        json: { type: string }  # 120-token JSON string
    EmbedRequest:
      type: object
      properties:
        chunk_ids: { type: array, items: { type: string }, minItems: 1, maxItems: 1000 }
        objects:   { type: array, items: { type: object }, description: "Optional ad-hoc texts" }
        compute:   { type: array, items: { type: string, enum: [ splade, qwen ] }, default: [ "splade", "qwen" ] }
        persist:   { type: boolean, default: true }
    EmbedResponse:
      type: object
      properties:
        embedded: { type: integer }
        failed:   { type: integer }
    RetrieveRequest:
      type: object
      required: [ query ]
      properties:
        query: { type: string }
        intent: { type: string, enum: [ pico, endpoint, adverse_event, dose, eligibility, contraindication, lab ] }
        filters:
          type: object
          properties:
            code: { type: object, properties: { system: {type: string}, value: {type: string} } }
            section: { type: string }
            source: { type: string, enum: [ pmc, cti, spl, guideline ] }
            date_from: { type: string, format: date }
            date_to: { type: string, format: date }
        topN: { type: integer, default: 20, minimum: 1, maximum: 200 }
        rerank: { type: boolean, default: true }
        explain: { type: boolean, default: true }
    RetrieveResponse:
      type: object
      properties:
        query: { type: string }
        results:
          type: array
          items:
            type: object
            properties:
              chunk_id: { type: string }
              doc_id: { type: string }
              title_path: { type: string }
              snippet: { type: string }
              start_char: { type: integer }
              end_char: { type: integer }
              score: { type: number }
              components:
                type: object
                properties:
                  bm25: { type: number }
                  splade: { type: number }
                  dense: { type: number }
                  reranker: { type: number, nullable: true }
              highlights: { type: array, items: { type: string } }
    ELRequest:
      type: object
      required: [ mentions ]
      properties:
        mentions:
          type: array
          items:
            type: object
            required: [ doc_id, chunk_id, start, end, text, type ]
            properties:
              doc_id: { type: string }
              chunk_id: { type: string }
              start: { type: integer }
              end: { type: integer }
              text: { type: string }
              type: { type: string }
              context: { type: string }
              allow_ontologies: { type: array, items: { type: string } }
    ELResponse:
      type: object
      properties:
        mappings:
          type: array
          items:
            type: object
            properties:
              mention_span: { type: array, items: { type: integer }, minItems: 2, maxItems: 2 }
              chosen_id: { type: string }
              ontology: { type: string }
              score: { type: number }
              evidence_span:
                type: object
                properties:
                  doc_id: { type: string }
                  chunk_id: { type: string }
                  start: { type: integer }
                  end: { type: integer }
                  quote: { type: string }
              alternates:
                type: array
                items:
                  type: object
                  properties:
                    iri: { type: string }
                    ontology: { type: string }
                    score: { type: number }
                    why: { type: string }
    ExtractRequest:
      type: object
      properties:
        doc_id: { type: string }
        chunk_ids: { type: array, items: { type: string } }
        strict: { type: boolean, default: true }
      oneOf:
        - required: [ doc_id ]
        - required: [ chunk_ids ]
    ExtractResponse:
      type: object
      properties:
        objects: { type: array, items: { type: object } }  # schema depends on 'kind'
    KGWriteRequest:
      type: object
      required: [ operations ]
      properties:
        operations:
          type: array
          items:
            type: object
            properties:
              op: { type: string, enum: [ upsert_node, upsert_edge ] }
              payload: { type: object }
              provenance: { $ref: '#/components/schemas/Provenance' }
    KGWriteResponse:
      type: object
      properties:
        upserted_nodes: { type: integer }
        upserted_edges: { type: integer }
    Provenance:
      type: object
      required: [ model, version, prompt_hash, schema_hash, ts ]
      properties:
        model: { type: string }
        version: { type: string }
        prompt_hash: { type: string }
        schema_hash: { type: string }
        ts: { type: string, format: date-time }
    Error:
      type: object
      properties:
        error:
          type: object
          properties:
            code: { type: string }
            message: { type: string }
            details: { type: array, items: { type: object } }
            retriable: { type: boolean }
```

### 13.1.1 Request/Response examples (selected)

**/retrieve (intent=endpoint)**

```json
{
  "query": "hazard ratio for all-cause mortality with sacubitril valsartan vs enalapril",
  "intent": "endpoint",
  "filters": { "source": "pmc" },
  "topN": 10,
  "rerank": true,
  "explain": true
}
```

**200 OK**

```json
{
  "query":"hazard ratio for all-cause mortality with sacubitril valsartan vs enalapril",
  "results":[
    {
      "chunk_id":"9c1e...f",
      "doc_id":"sha1:abc...",
      "title_path":"Results > Primary endpoint",
      "snippet":"The primary endpoint was all-cause mortality (HR 0.76; 95% CI 0.61–0.95; p=0.012)...",
      "start_char": 1023,
      "end_char": 1130,
      "score":0.912,
      "components":{"bm25":0.71,"splade":0.93,"dense":0.82,"reranker":0.91},
      "highlights":["HR 0.76","95% CI 0.61–0.95"]
    }
  ]
}
```

**/map/el**

```json
{
  "mentions": [
    {
      "doc_id":"sha1:abc...",
      "chunk_id":"9c1e...f",
      "start": 32, "end": 54,
      "text":"sacubitril/valsartan",
      "type":"drug",
      "context":"... HR 0.76 with sacubitril/valsartan vs enalapril ..."
    }
  ]
}
```

**200 OK**

```json
{
  "mappings": [
    {
      "mention_span":[32,54],
      "chosen_id":"rxnorm:1737755",
      "ontology":"RxNorm",
      "score":0.94,
      "evidence_span":{"doc_id":"sha1:abc...","chunk_id":"9c1e...f","start":32,"end":54,"quote":"sacubitril/valsartan"},
      "alternates":[{"iri":"rxnorm:1996170","ontology":"RxNorm","score":0.63,"why":"salt form (maleate)"}]
    }
  ]
}
```

### 13.2 Endpoint‑level behaviors and constraints

* **/ingest/** endpoints:

  * Validate IDs with deterministic validators (see §5.5). If any invalid → `400 VALIDATION_ERROR`.
  * Respect **robots/licensing** (PMC OA subset only for bulk).
  * Produce IR as **NDJSON**; return object store URI.
  * **Sync mode**: run entire flow; **Async mode** (`sync=false`): enqueue job; return `{status:"queued", job_id}` and stream progress via SSE `/jobs/{id}/events`.

* **/chunk**:

  * Uses configured **profiles** (§14). If `target_tokens/overlap` present, override profile for this request (guardrails: see schema limits).
  * Returns chunks and facets (if `produce_facets=true`); persists to stores when `persist=true`.

* **/embed**:

  * If `objects[]` provided, compute embeddings/SPLADE for ad‑hoc payloads; never persisted unless `persist=true`.

* **/retrieve**:

  * Executes **BM25 + SPLADE + Qwen** parallel retrieval and **fusion** (§6.5).
  * If `explain=true`, returns component scores & highlight snippets.
  * Enforces **license gating** on returned texts (may redact concept labels for restricted tiers).

* **/map/el**:

  * Generates candidates using **concepts_v1** (OpenSearch + Neo4j KNN) and deterministic IDs.
  * Adjudicates with LLM; returns `score`. Accept threshold is enforced **downstream** when writing to KG.

* **/extract/**:

  * `kind` controls schema; `strict=true` rejects extra fields.
  * Fails if spans cannot be located back into `doc_id` text — **span‑grounding required**.

* **/kg/write**:

  * Validates node/edge payloads against internal **JSON Schemas** (per label/rel).
  * Ensures **provenance** presence and stores it on `:WAS_GENERATED_BY` activities.

---

## 13.3 Non‑functional requirements (NFRs) & SLOs

* **Latency P95**: `/retrieve` (rerank=false) ≤ **450 ms**, (rerank=true) ≤ **700 ms**.
* **Availability (monthly)**: 99.9% for read endpoints; 99.5% for write endpoints.
* **Throughput**: ≥ 250 RPS sustained on `/retrieve` cluster.
* **Security**: TLS 1.2+, mTLS for internal services; all secrets in Vault/KMS; JWT lifetime ≤ 60 min.
* **Audit**: Every write endpoint emits **audit log** with subject, scopes, resource IDs, and truncated payload hash.

---

# 14) Config (YAML), validation, and dynamic reload

## 14.0 Principles

* **Single source of truth** (`config.yaml`) with **JSON‑Schema** validation.
* **Three layers** of precedence: **env overrides** > **secrets** > **base YAML**.
* **Dynamic reload** (SIGHUP or `/admin/reload` with `admin:*`) for non‑critical knobs (weights, thresholds); model paths and cluster endpoints require restart/rolling deploy.

---

## 14.1 Canonical `config.yaml` (production defaults)

```yaml
env: prod
region: us-east-1
service:
  name: medkg
  api_version: 1.0.0
  http:
    port: 8080
    cors_origins: ["https://*.internal.<org>"]
    rate_limit_per_minute: 1200
    max_body_mb: 20
  auth:
    oauth2:
      token_url: "https://auth.<org>/oauth2/token"
      jwks_url: "https://auth.<org>/.well-known/jwks.json"
      audience: "medkg"
    api_keys: { enabled: true }

storage:
  object_store:
    driver: s3
    bucket: "medkg-prod-artifacts"
    prefix: "v1/"
    sse: "aws:kms"
  opensearch:
    endpoint: "https://os-prod.<org>:9200"
    username: "${OS_USER}"
    password: "${OS_PASS}"
    indices:
      chunks: "chunks_v1"
      concepts: "concepts_v1"
  neo4j:
    uri: "neo4j+s://neo4j-prod.<org>:7687"
    username: "${NEO4J_USER}"
    password: "${NEO4J_PASS}"
    database: "neo4j"
    vector:
      chunks_index: "chunk_qwen_idx"
      concepts_index: "concept_qwen_idx"

licenses:
  enforce: true
  default_tier: "public"
  allowlists:
    snomed_member_countries: ["US","UK","CA", "AU", "NZ", "DE", "SE"]   # example
  deny_return_text_for: ["MedDRA","SNOMEDCT","UMLS"]
  allow_return_ids_for: ["MedDRA","SNOMEDCT","UMLS"]

chunking:
  imrad:     { target_tokens: 600, overlap: 0.15, tau_coh: 0.55 }
  registry:  { target_tokens: 400, overlap: 0.15, tau_coh: 0.55 }
  spl:       { target_tokens: 450, overlap: 0.15, tau_coh: 0.55 }
  guideline: { target_tokens: 400, overlap: 0.15, tau_coh: 0.55 }
  tables_atomic: true
  overlap_hard_boundary: false

retrieval:
  fusion_weights: { splade: 0.5, dense: 0.35, bm25: 0.15 }
  reranker: { enabled: true, model: "qwen3-rerank", topN: 100 }
  bm25:
    boosts: { title_path: 2.0, facet_json: 1.6, table_lines: 1.2, body: 1.0 }
    k1: 0.9
    b: 0.35
  splade:
    model: "naver/splade-v3"
    doc_topK: 400
    min_weight: 0.05
  dense:
    model: "qwen3-embedding-8b"
    dim: 4096
    metric: "cosine"

el:
  k_candidates: 20
  accept_threshold: 0.70
  id_validators: ["RxCUI","UNII","NCT","UDI","LOINC","ICD11","SNOMED"]
  llm:
    model: "qwen2.5-72b-instruct"
    temperature: 0.1
    max_tokens: 512
    timeout_ms: 15000

extraction:
  schemas: ["pico.json","effects.json","ae.json","dose.json","eligibility.json"]
  shacl_profiles: ["units_ucum.ttl","ids_codes.ttl"]
  llm:
    model: "qwen2.5-72b-instruct"
    temperature: 0.0
    max_tokens: 1024
  numeric_parsing:
    decimal_comma: true
    dash_variants: ["–","—","-"]

mineru:
  endpoint: "http://mineru:9000"
  ocr_langs: ["en","es","fr","de"]
  timeout_ms: 60000

catalog:
  refresh_cron:
    snomed_ct: "0 4 1 JAN,APR,JUL,OCT *"
    icd11: "0 5 1 MAR,SEP *"
    mondo: "0 3 1 * *"
    hpo: "0 2 1 * *"
    loinc: "0 1 1 JAN,JUL *"
    rxnorm: "0 0 * * MON"
    gsrs_unii: "0 6 1 * *"
    meddra: "0 4 1 JAN,APR,JUL,OCT *"
    gudid: "0 */6 * * *"

orchestration:
  queue: { driver: "kafka", brokers: ["kafka-1:9092","kafka-2:9092"] }
  topics:
    ingest_requests: "ingest.requests.v1"
    ingest_results: "ingest.results.v1"
    chunk_requests:  "chunk.requests.v1"
    embed_requests:  "embed.requests.v1"
    embed_results:   "embed.results.v1"
    mapping_events:  "mapping.events.v1"

observability:
  prometheus: { endpoint: "http://prometheus:9090" }
  otel:
    exporter: "otlp"
    endpoint: "http://otel-collector:4317"
  logging:
    level: "INFO"
    sink: "stdout"
    json: true
  dashboards:
    grafana_folder: "MedKG"

security:
  cors_allow_credentials: false
  tls_min_version: "1.2"
  mTLS_internal: true
  ip_allowlist_admin: ["10.0.0.0/8"]

retention:
  object_store_days: 365
  logs_days: 30
  metrics_days: 14
  os_snapshot_cron: "0 3 * * *"    # daily
  neo4j_backup_cron: "0 4 * * *"

feature_flags:
  enable_neighbor_merge: true
  enable_multi_granularity: true
  enable_license_masking: true
```

### 14.2 Config validation schema (`config.schema.json`)

* **Enforce types, ranges, and required sections.** Tooling: `ajv` or `pydantic` for load‑time validation.

Key validations:

* `retrieval.fusion_weights` **must** sum to 1.0 ± 0.01.
* `dense.dim` **must** be `4096` (Qwen3‑8B default).
* `el.accept_threshold ∈ [0.5, 0.95]`.

### 14.3 Environment overrides

* **ENV → YAML mapping:** any dotted path can be overridden by env var: `MEDKG__RETRIEVAL__RERANKER__ENABLED=false`.
* **Secrets:** never in YAML; use `${VAR}` placeholders; resolve via Vault/KMS at startup.

### 14.4 Dynamic reload

* **Hot‑reloadable:** `retrieval.fusion_weights`, `feature_flags`, `chunking.*`, `licenses.*`.
* Endpoint: `POST /admin/reload` (scope `admin:*`) → validates new config, swaps atomically, emits event to Kafka `config.updates`.

---

# 15) Orchestration & infrastructure (DAGs, K8s, storage, CI/CD)

## 15.0 Architecture overview (text)

* **Control plane:** Kubernetes (prod/stage/dev namespaces); **service mesh** optional (Istio/Linkerd) for mTLS.
* **Data plane:**

  * **OpenSearch** cluster for BM25/SPLADE indices.
  * **Neo4j** causal cluster (3 cores + read replicas) with **vector index** enabled.
  * **Object store** (S3/MinIO) for IR/NDJSON artifacts and MinerU outputs.
  * **Kafka/Redpanda** for job queues & audit events.
  * **GPU nodes** (A100/L40S) for Qwen embedding/rerank and LLM adjudication/extraction.
* **Observability:** Prometheus + Grafana; logs to OpenSearch or Loki; tracing via OpenTelemetry → Jaeger/Tempo.
* **Security:** mTLS between services; Vault for secrets; WAF in front of API.

---

## 15.1 End‑to‑end DAG (Airflow example)

> You can implement in **Airflow** (shown), **Prefect**, or **Dagster**. The key is **idempotent tasks**, **exactly‑once** semantics for writes, and **span/provenance preservation**.

### 15.1.1 DAG definition (Airflow, Python)

```python
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    "owner": "medkg",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="medkg_ingest_build_v1",
    start_date=days_ago(1),
    schedule_interval=None,
    default_args=default_args,
    catchup=False,
    max_active_runs=8,
    tags=["medkg","ingest"],
) as dag:

    ingest = KubernetesPodOperator(
        task_id="ingest_sources",
        name="ingest-sources",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-ingest:1.5.2",
        cmds=["python","/app/ingest_entry.py"],
        arguments=["--payload","{{ dag_run.conf['ingest_payload'] | tojson }}"],
        env_vars={"CONFIG": "/etc/medkg/config.yaml"},
        get_logs=True,
        is_delete_operator_pod=True,
        resources={"request_cpu":"500m","request_memory":"1Gi","limit_cpu":"1","limit_memory":"2Gi"}
    )

    parse = KubernetesPodOperator(
        task_id="parse_to_ir",
        name="parse-to-ir",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-parser:1.4.0",
        cmds=["python","/app/parse_entry.py"],
        arguments=["--doc-uris","{{ ti.xcom_pull('ingest_sources','doc_uris') }}"],
        get_logs=True,
    )

    chunk = KubernetesPodOperator(
        task_id="chunk_semantic",
        name="chunk-semantic",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-chunker:1.3.1",
        cmds=["python","/app/chunk_entry.py"],
        arguments=["--doc-ids","{{ ti.xcom_pull('parse_to_ir','doc_ids') }}","--profile","{{ dag_run.conf.get('profile','imrad') }}"],
        get_logs=True,
    )

    embed_splade = KubernetesPodOperator(
        task_id="embed_splade",
        name="embed-splade",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-splade:1.2.0",
        cmds=["python","/app/expand_doc.py"],
        arguments=["--chunk-ids","{{ ti.xcom_pull('chunk_semantic','chunk_ids') }}"],
        get_logs=True,
        resources={"request_cpu":"4","request_memory":"8Gi","limit_cpu":"8","limit_memory":"16Gi"}
    )

    embed_qwen = KubernetesPodOperator(
        task_id="embed_qwen",
        name="embed-qwen",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-qwen-embed:1.2.3",
        cmds=["python","/app/embed.py"],
        arguments=["--chunk-ids","{{ ti.xcom_pull('chunk_semantic','chunk_ids') }}"],
        container_resources={
            "limits": {"nvidia.com/gpu": 1}
        },
        node_selector={"kubernetes.io/instance-type":"g5.2xlarge"},
        tolerations=[{"key":"nvidia.com/gpu","operator":"Exists"}],
        get_logs=True,
    )

    index = KubernetesPodOperator(
        task_id="index_opensearch",
        name="index-opensearch",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-indexer:1.1.0",
        cmds=["python","/app/index_chunks.py"],
        arguments=["--chunks","{{ ti.xcom_pull('chunk_semantic','chunk_ids') }}"],
        get_logs=True,
    )

    onto_sync = KubernetesPodOperator(
        task_id="ontology_sync",
        name="ontology-sync",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-catalog:1.3.0",
        cmds=["python","/app/ensure_concepts.py"],
        arguments=["--doc-ids","{{ ti.xcom_pull('parse_to_ir','doc_ids') }}"],
        get_logs=True,
    )

    map_extract = KubernetesPodOperator(
        task_id="map_and_extract",
        name="map-extract",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-extract:1.6.0",
        cmds=["python","/app/run_extract.py"],
        arguments=["--doc-ids","{{ ti.xcom_pull('parse_to_ir','doc_ids') }}","--write-kg","true"],
        container_resources={"limits":{"nvidia.com/gpu":1}},
        node_selector={"kubernetes.io/instance-type":"g5.2xlarge"},
        get_logs=True,
    )

    eval = KubernetesPodOperator(
        task_id="evaluate",
        name="evaluate",
        namespace="medkg",
        image="ghcr.io/<org>/medkg-eval:1.0.2",
        cmds=["python","/app/run_eval.py"],
        arguments=["--doc-ids","{{ ti.xcom_pull('parse_to_ir','doc_ids') }}"],
        get_logs=True,
    )

    ingest >> parse >> chunk >> [embed_splade, embed_qwen] >> index >> onto_sync >> map_extract >> eval
```

**Key characteristics**

* **Idempotency:** every task writes outputs under a **content‑addressed** path (sha1) to object store; re‑runs are skips unless `--force`.
* **Retries:** 2 with exponential backoff.
* **Concurrency:** GPU tasks separated; node selectors/tolerations route to GPU pool.

---

## 15.2 Kubernetes deployment (core services)

### 15.2.1 Deployments (abbreviated manifests)

**API Gateway**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: medkg-api, namespace: medkg }
spec:
  replicas: 4
  selector: { matchLabels: { app: medkg-api } }
  template:
    metadata: { labels: { app: medkg-api } }
    spec:
      containers:
        - name: app
          image: ghcr.io/<org>/medkg-api:1.8.1
          ports: [ { containerPort: 8080 } ]
          envFrom: [ { secretRef: { name: medkg-secrets } } ]
          env:
            - { name: CONFIG, value: /etc/medkg/config.yaml }
          volumeMounts:
            - { name: config, mountPath: /etc/medkg }
          readinessProbe: { httpGet: { path: /v1/health, port: 8080 }, initialDelaySeconds: 5, periodSeconds: 10 }
          livenessProbe:  { httpGet: { path: /v1/health, port: 8080 }, initialDelaySeconds: 10, periodSeconds: 20 }
          resources:
            requests: { cpu: "500m", memory: "1Gi" }
            limits:   { cpu: "2", memory: "3Gi" }
      volumes:
        - name: config
          configMap: { name: medkg-config }
---
apiVersion: v1
kind: Service
metadata: { name: medkg-api, namespace: medkg }
spec:
  type: ClusterIP
  selector: { app: medkg-api }
  ports: [ { port: 80, targetPort: 8080 } ]
```

**Qwen Embed Worker (GPU)**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: qwen-embed, namespace: medkg }
spec:
  replicas: 3
  selector: { matchLabels: { app: qwen-embed } }
  template:
    metadata: { labels: { app: qwen-embed } }
    spec:
      nodeSelector: { "nvidia.com/gpu.product": "A10" }
      tolerations: [ { key: "nvidia.com/gpu", operator: "Exists", effect: "NoSchedule" } ]
      containers:
        - name: worker
          image: ghcr.io/<org>/medkg-qwen-embed:1.2.3
          resources:
            limits: { "nvidia.com/gpu": 1, cpu: "2", memory: "16Gi" }
            requests: { "nvidia.com/gpu": 1, cpu: "1", memory: "12Gi" }
          env: [ { name: MODEL_PATH, value: /models/qwen3-embedding-8b } ]
```

**SPLADE Expander (CPU)**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: splade-expander, namespace: medkg }
spec:
  replicas: 4
  selector: { matchLabels: { app: splade-expander } }
  template:
    metadata: { labels: { app: splade-expander } }
    spec:
      containers:
        - name: worker
          image: ghcr.io/<org>/medkg-splade:1.2.0
          resources:
            requests: { cpu: "4", memory: "8Gi" }
            limits:   { cpu: "8", memory: "16Gi" }
```

**HPA (API)**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: medkg-api-hpa, namespace: medkg }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: medkg-api }
  minReplicas: 4
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 65 } }
```

**PodDisruptionBudget**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: medkg-api-pdb, namespace: medkg }
spec:
  minAvailable: 3
  selector: { matchLabels: { app: medkg-api } }
```

### 15.2.2 Ingress and TLS

* Use **Ingress** with **cert‑manager** for TLS; **WAF** rules for basic bot/scan protection.
* **mTLS** via service mesh for **internal** service‑to‑service calls.

---

## 15.3 Data stores & operational settings

### 15.3.1 OpenSearch

* **Topology:** 3 master, 6 data nodes (i3en or gp3 storage), 1 coordinator.
* **Shards:** `chunks_v1` 6 shards, 1 replica; `concepts_v1` 3 shards, 1 replica.
* **ILM:** hot‑warm policy; hot for 30 days, warm thereafter; force‑merge to 1 seg after 7 days.
* **Snapshots:** daily to S3 (`retention.object_store_days` governs).
* **Index templates:** use mappings in §6.3 and §5.3.

### 15.3.2 Neo4j

* **Cluster:** 3 core + 2 read replicas.
* **Heap/pagecache:** heap = 32G, pagecache = 64G (tune based on dataset).
* **Plugins:** GDS (optional), APOC; **vector index enabled**.
* **Backups:** nightly `neo4j-admin backup` to S3 with PITR (WAL retention 7 days).
* **Constraints/indexes:** from §9.3 and vector index from §9.4.

### 15.3.3 Object store (S3/MinIO)

* **Buckets:**

  * `medkg-prod-artifacts` (IR, NDJSON, MinerU HTML)
  * `medkg-prod-embeddings` (optional FAISS shards)
  * `medkg-prod-snapshots` (backups)
* **Layout (partitioned):** `s3://medkg-prod-artifacts/source=<pmc|cti|spl>/ingest_date=YYYY-MM-DD/{doc_id}.ndjson`
* **Versioning:** enabled; **SSE‑KMS** enabled.

### 15.3.4 Kafka (or Redpanda)

* **Topics:** from config (see §14.1 `orchestration.topics`).
* **Retention:** 7 days for requests/results; 30 days for audit.
* **Schema registry:** JSON Schema; set compatibility to **BACKWARD**.

---

## 15.4 Message/event schemas (JSON Schema)

**`ingest.requests.v1`**

```json
{
  "$id":"ingest.requests.v1",
  "type":"object",
  "properties":{
    "kind":{"type":"string","enum":["clinicaltrials","dailymed","pmc"]},
    "payload":{"type":"object"},
    "requested_by":{"type":"string"},
    "idempotency_key":{"type":"string","format":"uuid"}
  },
  "required":["kind","payload","requested_by","idempotency_key"]
}
```

**`embed.results.v1`**

```json
{
  "$id":"embed.results.v1",
  "type":"object",
  "properties":{
    "chunk_ids":{"type":"array","items":{"type":"string"}},
    "splade_count":{"type":"integer"},
    "dense_count":{"type":"integer"},
    "duration_ms":{"type":"integer"},
    "errors":{"type":"array","items":{"type":"string"}}
  },
  "required":["chunk_ids","duration_ms"]
}
```

**`mapping.events.v1`**

```json
{
  "$id":"mapping.events.v1",
  "type":"object",
  "properties":{
    "doc_id":{"type":"string"},
    "chunk_id":{"type":"string"},
    "mention":{"type":"string"},
    "chosen_id":{"type":"string"},
    "ontology":{"type":"string"},
    "score":{"type":"number"},
    "provenance":{"$ref":"#/definitions/prov"}
  },
  "definitions":{
    "prov":{
      "type":"object",
      "properties":{"model":{"type":"string"},"version":{"type":"string"},"ts":{"type":"string","format":"date-time"}}
    }
  },
  "required":["doc_id","chunk_id","mention","chosen_id","ontology","score","provenance"]
}
```

---

## 15.5 CI/CD (GitHub Actions example)

```yaml
name: medkg-ci

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements-dev.txt
      - run: pytest -q --maxfail=1 --disable-warnings

  build_images:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        svc: [ api, ingest, parser, chunker, splade, qwen-embed, indexer, extract, eval, catalog ]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - run: docker build -f docker/${{ matrix.svc }}.Dockerfile -t ghcr.io/<org>/medkg-${{ matrix.svc }}:${{ github.sha }} .
      - run: docker push ghcr.io/<org>/medkg-${{ matrix.svc }}:${{ github.sha }}

  deploy_prod:
    needs: build_images
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/k8s-set-context@v4
        with: { method: kubeconfig, kubeconfig: ${{ secrets.KUBECONFIG }} }
      - name: Render Helm values
        run: ./scripts/render_values.sh prod ${{ github.sha }}
      - name: Helm upgrade
        run: helm upgrade --install medkg ./helm/ -f ./helm/values-prod.yaml
```

**Quality gates**

* Lint (black/ruff), type checks (mypy), license checks for bundled data.
* Image scanning (Trivy/Grype).
* SAST (CodeQL).

---

## 15.6 Observability

* **Metrics (Prometheus):**

  * `http_requests_total{route,code}`
  * `retrieve_latency_ms_bucket`
  * `fusion_component_score{component}`
  * `el_accept_rate`
  * `extraction_span_grounding_failures`
  * `opensearch_query_latency_ms`
  * `neo4j_vector_latency_ms`
* **Alerts:**

  * P95 `/retrieve` latency > 900 ms (5m) → page.
  * EL acceptance < 0.6 (hourly rolling) → warn.
  * OpenSearch shard unassigned > 0 → page.
  * Neo4j core down < 3 → page.
* **Tracing:** propagate **OpenTelemetry**; instrument calls to OS/Neo4j/LLM; 0.1 sampling in prod (adjustable).

---

## 15.7 Security & compliance

* **Network:** private subnets for data stores; API behind ALB/NLB + WAF; egress via NAT with allowlists for NLM/FDA endpoints.
* **Secrets:** Vault KV; short‑lived DB credentials via dynamic secrets; rotation 30 days.
* **RBAC:** Kubernetes Namespaced roles; production deployments via GitOps (optional).
* **Data residency:** region‑pinned buckets; cross‑region DR optional.
* **Licensing enforcement:** gateway policy filters response fields (`licenses.deny_return_text_for`) by **caller tier**; logs redaction events.

---

## 15.8 Backups & disaster recovery

* **OpenSearch snapshots**: daily at 03:00 UTC to `medkg-prod-snapshots/os/`, **retain 30**.
* **Neo4j backups**: daily at 04:00 UTC to `medkg-prod-snapshots/neo4j/`, **retain 30**, PITR logs 7d.
* **Object store versioning**: enabled; lifecycle moves older than 90d to infrequent access/deep archive.
* **Restore runbook**: documented; test **quarterly** in staging.

---

## 15.9 Performance tuning & capacity planning

* **Retrieval blend**: monitor contributions of BM25/SPLADE/Dense; if SPLADE down, auto‑reweight to `dense=0.7, bm25=0.3`.
* **OpenSearch**: keep shard size 20–40 GB; refresh interval 30s; indexing buffer 10% heap.
* **Neo4j**: batch upserts (1000 nodes/edges/tx); set `dbms.memory.pagecache` to dataset working set.
* **GPU**: Qwen embed throughput target: ≥ 2.5K tokens/s/GPU; adjust batch size dynamically.

---

## 15.10 Runtime runbooks (common ops)

* **Hot config change**: `POST /admin/reload` with signed JWT (admin scope). Validate success via `/version` and metric `config_version`.
* **Scale retrieval**: HPA reacts to CPU; for I/O bound, scale via RPS autoscaler (KEDA on Kafka).
* **Index rebuild**: create `chunks_v2`, dual‑write, verify parity (Recall@20 delta < 2%), flip alias, drop old.
* **Catalog refresh**: triggered via `catalog.refresh` job; ensure license gates; diff counts (SNOMED/MedDRA deltas); rebuild synonyms file; invalidate OpenSearch analyzers (rolling restart).

---

## 15.11 Test plans (system level)

* **E2E** (nightly):

  1. Ingest 10 PMC OA + 10 SPL + 10 NCT.
  2. Chunk, embed, index.
  3. Run 50 gold medical queries; assert **Recall@20** and **nDCG@10** thresholds (see §12).
  4. EL adjudication on 100 mentions; assert acceptance ≥ 0.70 where deterministic IDs present.
  5. Extraction for PICO/effects/AEs; validate against gold JSON.
  6. KG write; run SHACL for UCUM/codes; expect 0 violations.

* **Chaos**:

  * Kill a Neo4j core: ensure writes failover appropriately; retries succeed.
  * Drop one OS data node: shards reassign within 5 minutes without read brownouts.

---

## 15.12 Cost controls

* **TTL policies** for transient topics (7d).
* **ILM warm/cold tiers** in OpenSearch.
* **Batching** for embeddings; **spot** GPU nodes for non‑urgent backfills.
* **Compression**: NDJSON gz; Kafka LZ4; API gzip.

---

## 15.13 Artifacts & code layout

```
repo/
  api/
    openapi.yaml
    handlers/ (ingest, chunk, embed, retrieve, map, extract, kg)
    middleware/ (auth, idempotency, tracing, licensing)
  services/
    ingest/ parser/ chunker/ splade/ qwen_embed/ indexer/ extract/ eval/ catalog/
  infra/
    k8s/ (deployments, hpAs, pdbs, ingress)
    helm/ (charts, values-*.yaml)
    terraform/ (vpc, eks, os, neo4j, s3, kafka)
  config/
    config.yaml
    config.schema.json
  schemas/
    concept.schema.json
    el_adjudicator.schema.json
    pico.json, effects.json, ae.json, dose.json, eligibility.json
    shacl/ (units_ucum.ttl, ids_codes.ttl)
  tests/
    e2e/, unit/, integration/
  scripts/
    render_values.sh
```

---

### Bottom line for Sections 13–15

* **Section 13** delivers a **fully specified API**: endpoints, schemas, auth, idempotency, errors, and examples—ready for scaffolding.
* **Section 14** provides a **single authoritative config**, schema validation, overrides, and hot‑reload semantics—ready for operationalization.
* **Section 15** defines the **production‑ready orchestration and infrastructure**: DAGs, K8s manifests, stores, observability, security, backups, CI/CD, runbooks, and test plans—ready for deployment.

Below is a **medicine‑only, deep‑dive expansion** for **Sections 16–19** of the plan. It is written so that software agents can convert it directly into specs, tests, CI gates, and runnable code. It incorporates your earlier constraints: **GPU‑only** (no CPU fallback), **MinerU run separated** (manual/dedicated GPU queue), and **vLLM on Ubuntu 24.04** for embeddings.

---

# 16) Acceptance criteria & comprehensive test plan (v1.0‑med)

## 16.1 Gold sets & benchmarks (what we measure against)

Create four gold sets (curatable in parallel):

1. **IMRaD articles (PMC OA)**

   * 120 articles across cardiology, oncology, infectious disease, neurology.
   * Annotations: **PICO**, **endpoints**, **effect sizes** (value, CI, p), **dose regimens**, and **key AEs**.
   * Include at least 40 tables with outcomes/AEs.

2. **ClinicalTrials.gov (v2 JSON) studies**

   * 150 studies (stratify: Phase 2/3, device/drug/biologic/behavioral).
   * Annotations: **Eligibility** (normalized logic), **Outcome measures**, **Results** (per arm), **AEs**.

3. **DailyMed SPL labels**

   * 100 labels (brand/generic variety; multiple routes).
   * Annotations: **Indications**, **Dosage & Administration**, **Warnings/Precautions**, **Adverse Reactions** (MedDRA PT mapping when possible).

4. **Guidelines** (WHO/CDC/College/NICE where allowed)

   * 60 recommendation units.
   * Annotations: **Recommendation text**, **strength**, **certainty (GRADE)**, **population/scope**.

> **Annotation process**

* Two independent clinicians/annotators + an adjudicator.
* Measure **inter‑annotator agreement**: Cohen’s κ (target ≥0.75 overall, ≥0.8 on categorical fields like AE grade).
* Store gold in versioned JSONL with **char offsets** into canonical text (exact spans).

## 16.2 Metrics & thresholds (go/no‑go)

**A. Chunking (intrinsic)**

* Median **intra‑chunk cosine** ≥ 0.60 (narrative) / ≥ 0.50 (eligibility/definitions).
* Median **inter‑chunk cosine** ≤ 0.45.
* **Boundary alignment**: ≥ 70% (IMRaD/SPL) / ≥ 60% (registry) of starts at section/heading changes.
* **No split** of tables or eligibility bullets (0 violations in test set).
* Size distribution: < 10% chunks < 120 tokens; 0 chunks > 1200 tokens.

**B. Retrieval (extrinsic)** using **fusion** (BM25 + SPLADE‑v3 + Qwen3‑8B), multi‑granularity on:

* **Recall@20**:

  * PICO queries ≥ 0.88
  * Endpoint/effect queries ≥ 0.85
  * AE queries ≥ 0.82
  * Dose queries ≥ 0.85
  * Eligibility queries ≥ 0.90
* **nDCG@10**: +5 points vs BM25 only (each intent family).
* **MRR**: report, no hard gate initially.

**C. Entity Linking (EL) adjudication**

* Deterministic IDs (RxCUI/UNII/LOINC/NCT/UDI): **accuracy ≥ 0.95**.
* Clinical concepts (SNOMED/MONDO/HPO/ICD‑11/MeSH): **accuracy ≥ 0.85**, **coverage ≥ 0.80** (fraction of mentions linked with confidence ≥ threshold).
* **Abstention rate** (score < τ): ≤ 0.15 on non‑ID concepts.

**D. Extraction quality (span‑grounded)**

* **PICO completeness** (all four elements present when available): ≥ 0.85.
* **Effect sizes** (type, value, CI, p): **F1 ≥ 0.80** (exact match on numeric values, tolerant CI formatting).
* **AEs mapping**: MedDRA PT + CTCAE grade exact: **accuracy ≥ 0.80**.
* **Dose normalization**: UCUM unit correctness ≥ 0.95; schedule fields (route/frequency/duration) ≥ 0.90.
* **Eligibility logic**: numeric thresholds exact ≥ 0.90; condition/lab code mapping ≥ 0.85.

**E. FHIR export**

* Valid **Evidence/EvidenceVariable** resources generated for ≥ 90% of studies with computable results and PICO.

**F. Performance & reliability (GPU‑only)**

* **vLLM embedding throughput**: ≥ 1,000 chunks/min/GPU (batch tuned; 4k‑dim).
* **SPLADE doc expansion**: complete 10k chunks/hr/GPU (target; adjust per GPU).
* Pipeline **retries** succeed ≥ 99% (transient errors).
* **No CPU fallback** occurred (0 events); GPU checks enforced.

**G. Provenance & validation**

* 100% of **asserted triples** have `doc_id`, `start_char`, `end_char`, and **verbatim quote**.
* **SHACL** profiles pass‑rate ≥ 0.98 (units, IDs, code presence, ranges).

**H. Operational SLOs**

* Retrieval API P95 latency for top‑50 candidates ≤ 300 ms (local), ≤ 600 ms (clustered).
* Indexing lag < 10 min for new IR (non‑PDF auto path); post‑MinerU lag depends on manual trigger.

> **Go/No‑Go:** release requires meeting all **A–E** gates, SLOs in **H**, and no regressions >2 points from the prior baseline on any metric.

## 16.3 Evaluation harness (how we compute the above)

* **Repo:** `eval/` with Python scripts using the IR & KG APIs.
* **Reproducibility:** fix random seeds; deterministic tokenizer; version model weights.
* **Data splits:** 70/15/15 train/dev/test; **test** remains frozen for sign‑off.
* **Chunking intrinsic**: compute sentence embeddings via vLLM; store per‑document metrics JSON.
* **Retrieval**: build query sets per intent; run BM25, SPLADE, Qwen, fusion, RRF; compute metrics; produce per‑intent plots.
* **EL**: match predicted IDs to gold with span overlaps ≥ 0.8 IoU; compute accuracy/coverage.
* **Extraction**: compare JSON outputs field‑wise with tolerance rules (numeric epsilon for effect sizes; flexible CI string).
* **FHIR validation**: run HL7 validators; count pass/fail per resource, log reasons.
* **Reports**: aggregate dashboards (JSON + HTML) under `eval/reports/YYYY‑MM‑DD/`.

## 16.4 CI/CD gates

* **PR gate** (GitHub Actions/CI):

  * Unit tests **and** eval smoke tests (subset: 10 docs per family) must pass.
  * Lint + schema validation.
  * GPU checks mocked in unit; full GPU tests in nightly.
* **Nightly full eval**: run complete metrics; publish historical trends; fail if any gated metric drops >2 points.
* **Release gate**: run full test sets + FHIR validation; sign‑off checklist (below).

## 16.5 Sign‑off checklist (release)

* [ ] All metrics meet thresholds (A–E, H).
* [ ] **No** CPU fallback events detected.
* [ ] Licenses validated (SNOMED/UMLS/MedDRA as configured).
* [ ] Provenance coverage = 100%.
* [ ] SHACL pass‑rate ≥ 0.98.
* [ ] Backups verified (Neo4j, indexes, object store).
* [ ] Rollback plan tested on staging.

---

# 17) Clinical‑specific implementation checklists (expanded)

## 17.1 Directory layout (monorepo)

```
/adapters/
  ctgov_v2/
  pmc_jats/
  dailymed_spl/
  devices_gudid/
  guidelines/
  pdf_ingest/           # download-only, no auto
/mineru_runner/         # GPU-only script or service
/ir/
  schemas/              # JSON Schemas for Document/Block/Table
  builder/              # mappers from adapters→IR
/chunker/
  rules/
  clinical_tagger/
  config/               # YAML profiles per doc family
/embeddings/
  qwen_vllm_client/
  splade_v3_expander/
/indexing/
  bm25_es/
  splade_es/
  vector_faiss/
/ontology/
  loaders/              # SNOMED, ICD-11, LOINC, RxNorm, HPO, MONDO, MeSH, UCUM
  lexicon/
/llm/
  prompts/
  json_schemas/         # pico.json, effects.json, ae.json, dose.json, eligibility.json
  runner/               # OpenAI-compatible client to vLLM
  validators/           # JSON+SHACL+ID checks
/kg/
  neo4j/
    constraints/
    shacl/
    writers/
    exporters/          # FHIR Evidence/EvidenceVariable
/retrieval/
  fusion/
  reranker/             # optional local rerank
/eval/
  datasets/
  scripts/
  reports/
/ops/
  ledger/               # ingestion status, doc states
  cli/                  # med ingest, mineru-run, postpdf-start
  docker/
  k8s/
/config/
  env/
  yaml/
/scripts/
/Makefile
```

## 17.2 Environment & secrets

* `VLLM_API_BASE`, `REQUIRE_GPU=1`, `CUDA_VISIBLE_DEVICES`, `ES_URL`, `FAISS_STORE_URI`, `NEO4J_URI`, `NEO4J_USER/PASSWORD (vault)`, `OBJECT_STORE_URI`, `LIC_SNOMED`, `LIC_UMLS`, `LIC_MEDDRA`.
* Use Vault/KMS; mount read‑only to pods; rotate quarterly.

## 17.3 Makefile targets (selected)

```
make env.check-gpu            # nvidia-smi + torch.cuda.is_available
make ingest.ctgov NCT=...     # auto pipeline (non-PDF)
make ingest.pmc PMCID=...     # auto pipeline (JATS)
make ingest.spl SETID=...     # auto pipeline (SPL)
make ingest.pdf URI=... KEY=DOC123
make mineru.run KEY=DOC123    # GPU-only
make postpdf.start KEY=DOC123 # chunk->facet->embed->index
make index.build               # build ES/FAISS with current embeddings
make eval.smoke                # 10-doc-per-family smoke metrics
make eval.full                 # full benchmark run
```

## 17.4 Docker Compose (GPU)

`docker-compose.gpu.yml` includes services:

* `vllm-emb`: Qwen3‑Embedding‑8B server (ports 8000).
* `mineru-gpu`: MinerU runner image (bind mounts for input/output).
* `es`: OpenSearch/Elasticsearch node.
* `faiss`: vector store API (if you wrap FAISS).
* `neo4j`: with APOC + n10s.
* `orchestrator`: Prefect/Airflow scheduler.
* All GPU services use `deploy.resources.reservations.devices: [gpu]` or `--gpus all`.

## 17.5 Orchestration (Prefect/Airflow)

### Flows

* **auto_flow_nonpdf**: `ingest → parse → IR → chunk → facet → embed → index → (optional) extract/map → KG`.
* **pdf_flow**: `ingest_pdf → (STOP) → mineru_run → IR → (STOP) → postpdf_start → chunk → facet → embed → index → ...`.
* **gpu guards**: first step checks GPU and vLLM availability; fail job if absent.

### Scheduling

* CTG delta ingests nightly; PMC/Guideline crawls weekly; SPL weekly.
* MinerU runs via **manual trigger** or **GPU queue**.

## 17.6 Logs, monitoring, and dashboards

* **Prometheus** metrics from each service:

  * `mineru_pages_sec`, `mineru_failures_total`, `embed_chunks_sec`, `splade_docs_sec`, `retrieval_latency_ms`, `index_size_bytes`, `neo4j_write_tps`.
* **Grafana dashboards**:

  * GPU utilization (vLLM/SPLADE/MinerU), pipeline throughput, error rates, retrieval latency, acceptance metrics over time.
* **Alerting**:

  * vLLM down; GPU not visible; ES/Neo4j unhealthy; acceptance regression in nightly.

## 17.7 Testing strategy

* **Unit**: adapters, IR builder, chunker boundaries, ID validators, UCUM conversion, SHACL shapes.
* **Integration**: end‑to‑end on a small fixture set (1 per source), writing to staging Neo4j and ES/FAISS.
* **Chaos**: kill vLLM container; ensure embed stage fails gracefully (no CPU fallback) and ledger remains consistent.
* **Load**: 100k chunks embed/index; measure throughput/latency; ensure memory headroom.

## 17.8 Release procedure

1. Freeze model versions (`qwen3-embedding-8b@<sha>`, SPLADE ckpt@version).
2. Run **eval.full**; publish report.
3. Staging rollout; reindex a slice; smoke tests.
4. Production rollout with **canary** (10% of ingestion); monitor SLOs.
5. Full enablement; tag release; back up Neo4j & indexes.

---

# 18) LLM prompt suites & strict schemas (expanded)

**Global rules:**

* **OpenAI‑compatible JSON mode**; `response_format={"type":"json_object"}`.
* **Max output** per call: 2,000 tokens (tight for extractors).
* **Temperature**: 0.0–0.2 (deterministic); **top_p**: 1.0.
* **Retries**: up to 2 on invalid JSON; minimal re‑prompt: “Return valid JSON only.”
* **No chain‑of‑thought**: request short justifications only when necessary, not internal reasoning.
* **Span‑grounding mandatory**: every atomic fact includes `{doc_id, start, end, quote}`.

## 18.1 JSON Schemas (validator‑enforced)

### `pico.json`

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties":{
    "population":{"type":"string","minLength":3},
    "interventions":{"type":"array","items":{
      "type":"object","properties":{
        "drug":{"type":"object","properties":{"rxcui":{"type":"string"},"label":{"type":"string"}},"required":["label"]},
        "device":{"type":"object","properties":{"udi_di":{"type":"string"},"label":{"type":"string"}}},
        "procedure":{"type":"string"},
        "dose":{"type":"object","properties":{
          "amount":{"type":"number"},"unit":{"type":"string"},
          "route":{"type":"string"},"frequency_per_day":{"type":"number"},
          "duration_days":{"type":"number"}}}
      }}},
    "comparators":{"type":"array","items":{"type":"string"}},
    "outcomes":{"type":"array","items":{"type":"string"}},
    "timeframe":{"type":"string"},
    "evidence_spans":{"type":"array","items":{"type":"object",
      "properties":{"doc_id":{"type":"string"},"start":{"type":"integer"},"end":{"type":"integer"},"quote":{"type":"string"}},
      "required":["doc_id","start","end","quote"]}}
  },
  "required":["population","interventions","outcomes","evidence_spans"]
}
```

### `effects.json`

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties":{
    "outcome":{"type":"string"},
    "type":{"enum":["HR","RR","OR","MD","SMD"]},
    "value":{"type":"number"},
    "ci_low":{"type":"number"},
    "ci_high":{"type":"number"},
    "p_value":{"type":"number","minimum":0,"maximum":1},
    "n_total":{"type":"integer","minimum":1},
    "arm_sizes":{"type":"object","properties":{"int":{"type":"integer"},"comp":{"type":"integer"}}},
    "model":{"type":"string"},
    "time_unit_ucum":{"type":"string"},
    "evidence_spans":{"type":"array","items":{"type":"object","properties":{
      "doc_id":{"type":"string"},"start":{"type":"integer"},"end":{"type":"integer"},"quote":{"type":"string"}}, "required":["doc_id","start","end","quote"]}}
  },
  "required":["outcome","type","value","ci_low","ci_high","evidence_spans"]
}
```

### `ae.json`

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties":{
    "term":{"type":"string"},
    "meddra_pt":{"type":"string"},
    "grade":{"type":"string"},
    "count":{"type":"integer","minimum":0},
    "denom":{"type":"integer","minimum":1},
    "arm":{"enum":["intervention","comparator","overall"]},
    "serious":{"type":"boolean"},
    "evidence_spans":{"type":"array","items":{"type":"object","properties":{
      "doc_id":{"type":"string"},"start":{"type":"integer"},"end":{"type":"integer"},"quote":{"type":"string"}}, "required":["doc_id","start","end","quote"]}}
  },
  "required":["term","count","denom","arm","evidence_spans"]
}
```

### `dose.json`

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties":{
    "drug":{"type":"object","properties":{"rxcui":{"type":"string"},"label":{"type":"string"}},"required":["label"]},
    "amount":{"type":"number"},
    "unit":{"type":"string"},
    "route":{"type":"string"},
    "frequency_per_day":{"type":"number"},
    "duration_days":{"type":"number"},
    "evidence_spans":{"type":"array","items":{"type":"object","properties":{
      "doc_id":{"type":"string"},"start":{"type":"integer"},"end":{"type":"integer"},"quote":{"type":"string"}}, "required":["doc_id","start","end","quote"]}}
  },
  "required":["drug","amount","unit","evidence_spans"]
}
```

### `eligibility.json`

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties":{
    "type":{"enum":["inclusion","exclusion"]},
    "criteria":{"type":"array","items":{"type":"object","properties":{
      "text":{"type":"string"},
      "logic":{"type":"object","properties":{
        "age":{"type":"object","properties":{"gte":{"type":"number"},"lte":{"type":"number"}}},
        "lab":{"type":"object","properties":{"loinc":{"type":"string"},"op":{"enum":[">",">=","<","<=","="]},"value":{"type":"number"},"unit":{"type":"string"}}},
        "condition":{"type":"object","properties":{"system":{"type":"string"},"code":{"type":"string"}}},
        "temporal":{"type":"object","properties":{"op":{"enum":[">","<",">=","<="]},"days":{"type":"integer"}}}
      }}
    }, "required":["text"]}},
    "evidence_spans":{"type":"array","items":{"type":"object","properties":{
      "doc_id":{"type":"string"},"start":{"type":"integer"},"end":{"type":"integer"},"quote":{"type":"string"}}, "required":["doc_id","start","end","quote"]}}
  },
  "required":["type","criteria","evidence_spans"]
}
```

## 18.2 Prompt templates (with guardrails)

> **System (common)**
> “You are a medical information extractor. **Return only valid JSON** conforming to the provided schema. **Do not infer values** not explicitly stated. **Include verbatim evidence spans** (`doc_id`, `start`, `end`, `quote`) for **every** field you fill. If a field is absent, omit it.”

### EL adjudication (entity linking)

**User input template**

* Context (2–3 sentences with offsets), mention string, doc metadata (doc_id, section), **candidate list**: `{id, label, definition, synonyms, codes}`.

**Instruction**

* Prefer deterministic IDs (RxCUI, UNII, LOINC, NCT, UDI) when present and format/regex checks pass.
* If uncertain, pick best but lower `score`.

**Output JSON**
`{"mention_text":"...", "chosen_id":"...", "ontology":"...", "score":0.0-1.0, "evidence_span":{...}, "alternates":[...]}`

**Config**
`temperature=0.0`, `top_p=1.0`, `max_tokens=600`, `response_format=json`.

### PICO extraction

**Input**

* Chunk text (+path), doc_id, known hints (e.g., `arm_name`, `outcome_name`).
* Schema: `pico.json`.

**Instruction**

* Extract Population, Interventions (drug/device/procedure + dose), Comparators, Outcomes, Timeframe.
* Use exact words from text for **Population**; normalize dose to UCUM only in output fields (don’t change quotes).

**Config**
`temperature=0.1`, `max_tokens=900`.

### Effect extraction

**Input**

* Chunk(s) containing endpoints + effect statements; table rows if available.
* Schema: `effects.json`.

**Instruction**

* Only report effects where **endpoint + numeric** are in scope; capture `type`, `value`, `ci_low`, `ci_high`, `p_value`, `model`.
* Do **not** compute values; copy them with units/time.

**Config**
`temperature=0.0`, `max_tokens=700`.

### AE mapping

**Input**

* AE table chunks or narrative.
* Provide lexicon (MedDRA PT candidates) for terms found, if available.

**Instruction**

* Map to MedDRA PT if you can deduce unambiguously; otherwise keep `meddra_pt` empty and include `term`.
* Include `grade` if explicitly provided.

**Config**
`temperature=0.1`, `max_tokens=700`.

### Dose normalization

**Instruction**

* Extract dosing regimen; normalize to `{amount, unit, route, frequency_per_day, duration_days}`; convert units to UCUM but keep **quote** verbatim.
* If titration schedule, return multiple dose objects (array) respecting the schema (or single object with `note` is acceptable if schema expanded).

### Eligibility normalization

**Instruction**

* Split inclusion/exclusion; for each criterion, **fill logic** when clearly present (age, lab thresholds with LOINC + UCUM, conditions with code system).
* If ambiguous, leave `logic` empty but keep the `text`.

## 18.3 Error handling loop

* After each LLM call:

  * Validate JSON Schema; if invalid → **repair pass** with prompt: “The prior JSON was invalid due to: <errors>. Return valid JSON only matching the schema.”
  * Run **domain validators**: UCUM conversion, ID checks, numeric ranges.
  * If failing after repair → mark item `status="llm_invalid"` and add to review queue.

## 18.4 Few‑shot snippets (short)

* Include 1–2 examples per extractor with **positive** and **negative** cases (e.g., “no significant difference” → accept, but effect size may still be reported as non‑significant with p).
* **Ambiguity note**: “MI” could mean **myocardial infarction** or **mitral insufficiency**; only map if evidence clearly disambiguates (e.g., cardiology context, mention of troponin, STEMI/NSTEMI).

---

# 19) Governance, compliance, security & risk (medicine)

## 19.1 Licensing & IP controls

* **SNOMED CT**: require affiliate license for non‑member territories; enforce **ACL** so only licensed users access SNOMED‑derived fields.
* **UMLS**: require acceptance; some source vocabularies restrict redistribution; log source vocabulary usage for audits.
* **MedDRA**: subscription‑licensed; store PT/LLT mappings behind a **feature flag**; no redistribution in public endpoints.
* **LOINC, RxNorm, HPO, MONDO, MeSH, UCUM**: open/permits (respect attribution requirements).
* **PMC OA**: ingest only OA subset for full text; respect licenses per article.
* **DailyMed, GUDID**: public; include attribution.

**Automation**: on startup, the ontology loader reads `licenses.yml`; if a license is missing/invalid for a vocabulary → **disable** its loader and any dependent mappings (fail closed).

## 19.2 Privacy & PHI (future‑proofing if EHRs added)

* Treat all ingest as **non‑PHI** in v1.0; if EHRs later:

  * Use a **de‑identification** step and access control (RBAC) with audit logs.
  * **Encryption**: at rest (KMS) and in transit (TLS).
  * Data retention policy and **DSAR** (right to delete) for identifiable data.

## 19.3 Security controls

* **AuthN/Z**: service‑to‑service via mTLS + short‑lived JWT; user flows via OIDC.
* **Secrets**: Vault/KMS; no secrets in env/plain files.
* **Network**: private subnets for data stores; security groups restrict egress; WAF for public APIs.
* **Vulnerability mgmt**: weekly scans; base image pinning; dependency lockfiles; SBOM.
* **Supply chain**: signed images (cosign); policy checks (OPA/Gatekeeper).

## 19.4 Provenance & audit

* Every assertion carries **PROV**: `:WAS_GENERATED_BY → :ExtractionActivity {model,version,prompt_hash,schema_hash,ts}`.
* Keep **doc content hashes** and **IR hashes**; store MinerU run IDs/version for PDF‑derived docs.
* Immutable audit logs (WORM or log immutability setting in your log store).
* **Reproducibility**: all model version pins stored in KG config nodes and in build artifacts.

## 19.5 Model risk & human oversight

* **Selective prediction**: below threshold scores → review; never auto‑assert.
* **High‑impact edges** (e.g., `TREATS`, guideline claims) → second LLM + human spot‑check (sample ≥5%).
* **Change mgmt**: when model or threshold changes, run **backfill on dev** and compare deltas; require sign‑off for production migration.

## 19.6 Bias & fairness

* Ensure disease areas are **balanced** in gold sets; include female‑specific, pediatric, and under‑represented groups.
* Report metric breakdowns by condition/domain; track **systematic gaps** (e.g., rare disease coverage).

## 19.7 Data retention & deletion

* Define retention for raw sources (e.g., 2 years), IR (2 years), embeddings/indexes (regenerate on demand), KG (versioned; retained indefinitely with purge options per doc request).
* Implement purge pipeline that deletes doc → removes chunks → removes embeddings → removes KG nodes/edges referencing doc (or marks as orphaned with “deleted” provenance).

## 19.8 Disaster recovery (DR) & backups

* **Neo4j**: daily backup + WAL shipping; test restore monthly.
* **ES/FAISS**: snapshot to object store daily; index rebuild recipes documented.
* **Object store**: cross‑region replication on; lifecycle policies for versions.
* **Runbooks**: DR RPO ≤ 24h; RTO ≤ 8h (targets).

## 19.9 Legal & clinical disclaimers

* The system **does not provide medical advice**; for research/knowledge management only.
* Display provenance & quotes for all assertions.
* For public outputs, ensure only **license‑compliant** vocabularies are included.

## 19.10 Change management & versioning

* **Semantic versioning** for pipeline (`med‑kg vMAJOR.MINOR.PATCH`).
* **Ontology catalog version** node (per vocabulary: version, date).
* **Embeddings version** (model+timestamp) stored on `:Chunk`.
* **Index rebuilds** documented; ability to run two index generations in parallel and flip pointers atomically.

---

## Deliverables generated from this spec (what agents can output next)

* JSON Schemas (`pico.json`, `effects.json`, `ae.json`, `dose.json`, `eligibility.json`).
* SHACL shapes for units/IDs/codes (UCUM/LOINC/RxCUI/NCT).
* CI configs for **eval.smoke** & **eval.full** gates.
* Makefile targets and Docker Compose for GPU services (vLLM, MinerU).
* Prompts and validator code for each extractor & EL adjudicator.
* Grafana dashboards for SLOs and acceptance metrics.
