# Implementation Tasks

## 1. Domain Profiles & Configuration

- [x] 1.1 Define YAML profiles (IMRaD, Registry, SPL, Guideline) with target_tokens, overlap_pct, tau_coh
- [x] 1.2 Implement profile selector (based on Document.source_system and media_type)
- [x] 1.3 Add per-profile boundary rules (hard starts: heading depth change, registry section change, SPL LOINC change)

## 2. Clinical Intent Tagger

- [x] 2.1 Implement keyword heuristics for strong cues ("Inclusion Criteria", "Primary Outcome", "Adverse Events")
- [ ] 2.2 Train light classifier on Qwen sentence embeddings (weak supervision from keywords)
- [x] 2.3 Tag sentences with clinical intent (pico_*, adverse_event, dose, eligibility, recommendation, lab_value)
- [x] 2.4 Override with section-based hints (e.g., SPL Adverse Reactions section → adverse_event)

## 3. Coherence-Based Chunker

- [x] 3.1 Implement sentence splitting (spaCy or nltk)
- [ ] 3.2 Compute sentence embeddings via vLLM (Qwen3-Embedding-8B; batch API)
- [x] 3.3 Implement chunking algorithm (accumulate sentences; check coherence drop, token limit, intent switch)
- [x] 3.4 Add overlap strategy (carry forward last 15% sentences unless boundary aligns with heading)
- [x] 3.5 Enforce hard boundaries (heading, section, table start, eligibility kind switch)

## 4. Table Atomic Chunking

- [x] 4.1 Treat tables as atomic chunks (never split rows)
- [ ] 4.2 Generate table_digest via LLM (scope, metrics, units, arms, deltas) ≤200 tokens
- [x] 4.3 Store table_html + table_digest in Chunk meta

## 5. Guardrails & Special Cases

- [ ] 5.1 Never split endpoint/effect pairs (e.g., "HR 0.76, 95% CI 0.61-0.95; p=0.012" must stay together)
- [ ] 5.2 Never split list items or citations mid-item
- [ ] 5.3 Keep dose titration schedules in single chunk if possible; else neighbor-merge at query time
- [ ] 5.4 Tag facet with negation=true when uncertainty/negation detected (ConText/NegEx rules)

## 6. Facet Summary Generation

- [x] 6.1 Detect dominant intent per chunk (majority vote of sentence tags)
- [x] 6.2 Route to appropriate facet extractor (LLM with strict JSON schema)
- [x] 6.3 Validate facet JSON (schema + token budget ≤120)
- [x] 6.4 Store facet_json + facet_type on Chunk
- [ ] 6.5 Compute facet embedding (Qwen) if enabled

## 7. Embeddings & Indexing (GPU-only)

- [ ] 7.1 Compute chunk.embedding_qwen (4096-D) via vLLM
- [ ] 7.2 Compute SPLADE-v3 doc-side expansion (top-K=400 terms; GPU via Torch)
- [ ] 7.3 Build BM25/BM25F index (OpenSearch) with field boosts (title_path:2.0, facet_json:1.6, table_lines:1.2, body:1.0)
- [ ] 7.4 Fail-fast if GPU unavailable (no CPU fallback; consistent with MinerU/vLLM policy)

## 8. Multi-Granularity Indexing (Fallback)

- [ ] 8.1 Index paragraph-level blocks alongside chunks
- [ ] 8.2 Index section-level aggregations
- [ ] 8.3 Implement RRF or weighted fusion across granularities
- [ ] 8.4 Add sliding windows (512/768 tokens, 25% overlap) for problematic docs

## 9. Evaluation & Robustness

- [x] 9.1 Compute intrinsic metrics (intra-coherence median, inter-coherence median, boundary alignment %)
- [ ] 9.2 Compute extrinsic metrics (Recall@20, nDCG@10 on dev set per intent)
- [ ] 9.3 Implement neighbor-merge at query time (adjacent micro-chunks with min_cosine ≥ 0.60)
- [ ] 9.4 Monitor size distribution (< 10% chunks < 120 tokens; 0 chunks > 1200 tokens)

## 10. Neo4j & Search Integration

- [ ] 10.1 Create :Chunk nodes with properties (id, doc_id, text, type, section, tokens, start_char, end_char, facet_json, facet_type, embedding_qwen, splade_terms, createdAt)
- [ ] 10.2 Create (:Document)-[:HAS_CHUNK]->(:Chunk) edges
- [ ] 10.3 Create vector index chunk_qwen_idx (4096-D, cosine)
- [ ] 10.4 Optional: create (:Chunk)-[:SIMILAR_TO {score, model, ver}]->(:Chunk) edges for navigation

## 11. Testing

- [ ] 11.1 Unit tests for boundary detection (heading changes, section changes, table starts)
- [ ] 11.2 Unit tests for coherence calculation (cosine thresholds)
- [ ] 11.3 Integration tests (IR → chunks with profiles; validate sizes and overlaps)
- [ ] 11.4 Test GPU enforcement (vLLM unavailable → fail gracefully; no CPU embeddings)
- [ ] 11.5 Test edge cases (composite endpoints, dose titration, table notes/footnotes)

## 12. Documentation

- [ ] 12.1 Document domain profiles and when to use each
- [ ] 12.2 Create chunker tuning guide (adjusting target sizes, tau_coh, overlap)
- [ ] 12.3 Document fallback strategies (multi-granularity, sliding windows, neighbor-merge)
