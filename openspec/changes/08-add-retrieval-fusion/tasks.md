# Implementation Tasks

## 1. BM25/BM25F Retriever (OpenSearch)

- [ ] 1.1 Implement BM25F query (multi_match with field boosts: title_path:2.0, facet_json:1.6, table_lines:1.2, body:1.0)
- [ ] 1.2 Add biomed analyzer (synonym_graph filter with analysis/biomed_synonyms.txt from Concept Catalog)
- [ ] 1.3 Return top-N results with scores, doc_id, chunk_id
- [ ] 1.4 Add filters (facet_type, source, date_range)

## 2. SPLADE-v3 Retriever (OpenSearch)

- [ ] 2.1 Expand query via SPLADE query-encoder (GPU; produces weighted terms)
- [ ] 2.2 Construct OpenSearch query (bool.should with rank_feature clauses for each expanded term)
- [ ] 2.3 Return top-N results with SPLADE scores
- [ ] 2.4 Cache query expansions (60s TTL; key=hash(query_text))

## 3. Dense Retriever (Neo4j Vector KNN)

- [ ] 3.1 Embed query text via vLLM (Qwen3-Embedding-8B; 4096-D)
- [ ] 3.2 Execute KNN query (CALL db.index.vector.queryNodes('chunk_qwen_idx', k=200, queryEmbedding))
- [ ] 3.3 Return chunk_id + cosine scores
- [ ] 3.4 Cache query embeddings (60s TTL)

## 4. Fusion Strategies

- [ ] 4.1 Implement score normalization (min-max to [0,1] per retriever over union of top-K)
- [ ] 4.2 Implement weighted linear fusion (default: 0.50*SPLADE + 0.35*dense + 0.15*BM25)
- [ ] 4.3 Implement RRF (score = sum(1 / (k + rank_i)); k=60)
- [ ] 4.4 Allow runtime weights override (via API parameter)

## 5. Optional Reranker

- [ ] 5.1 Implement Qwen reranker (pairs: (query, candidate_text) where candidate_text = title_path + "\n" + first 600 chars)
- [ ] 5.2 Batch rerank (top-100 fused candidates)
- [ ] 5.3 Replace FusedScore with reranker score for final ranking (keep component scores for telemetry)
- [ ] 5.4 Add latency budget check (skip rerank if P95 exceeds SLO)

## 6. Intent Routing

- [ ] 6.1 Implement intent classifier (rules + light ML; intents: pico, endpoint, ae, dose, eligibility, general)
- [ ] 6.2 Per-intent field boosts (e.g., endpoint queries boost facet_json:2.0)
- [ ] 6.3 Per-intent filters (e.g., ae queries filter facet_type=ae)
- [ ] 6.4 Fallback to general if intent unclear

## 7. Ontology-Aware Query Expansion

- [ ] 7.1 Detect mentions in query (drug names, conditions, labs)
- [ ] 7.2 Resolve to Concept Catalog (RxCUI, SNOMED, LOINC)
- [ ] 7.3 Expand with synonyms (add to BM25 query with should clauses; SPLADE inherently expands)
- [ ] 7.4 Boost deterministic IDs (e.g., NCT, RxCUI exact matches → score *2)

## 8. Neighbor-Merge

- [ ] 8.1 Identify adjacent chunks (same doc_id; contiguous or nearby offsets)
- [ ] 8.2 Compute pairwise cosine (embedding_qwen)
- [ ] 8.3 Merge if cosine ≥ 0.60 and aggregated tokens ≤ 3000
- [ ] 8.4 Aggregate text, spans, and scores (max or weighted average)

## 9. Multi-Granularity Retrieval

- [ ] 9.1 Index paragraph-level blocks in separate OpenSearch index (paragraphs_v1)
- [ ] 9.2 Index section-level aggregations (sections_v1)
- [ ] 9.3 Run parallel queries (chunks, paragraphs, sections)
- [ ] 9.4 Fuse results via RRF

## 10. Retrieval API

- [ ] 10.1 Implement POST /retrieve (request: {query, intent?, filters?, topK?, rerank_enabled?})
- [ ] 10.2 Response: {results: [{chunk_id, score, scores_breakdown{bm25, splade, dense, fused, rerank?}, text, path, doc_id, meta}], query_meta: {intent_detected, expanded_terms, latency_ms}}
- [ ] 10.3 Add per-component score telemetry
- [ ] 10.4 Emit metrics (retrieve_latency_ms_bucket, retrieve_recall@k, component_scores)

## 11. Observability & Feature Flags

- [ ] 11.1 Log component scores per query (BM25, SPLADE, dense, fused, rerank)
- [ ] 11.2 Add feature flags (toggle SPLADE if model down; toggle reranker; adjust weights)
- [ ] 11.3 Cache result sets (key: hash(query + filters + modelVersions); TTL 60s)
- [ ] 11.4 Monitor drift (hit overlap vs last release; alert if < 0.6)

## 12. Testing

- [ ] 12.1 Unit tests for fusion strategies (mock scores → verify weighted/RRF outputs)
- [ ] 12.2 Integration tests (sample queries → verify top-K results include gold docs)
- [ ] 12.3 Eval harness (Recall@20, nDCG@10 per intent on dev set; must meet thresholds)
- [ ] 12.4 Load test (50 QPS burst, 10 QPS steady; measure P95 latency)

## 13. Documentation

- [ ] 13.1 Document fusion strategies and when to use each
- [ ] 13.2 Create retrieval tuning guide (adjusting weights, thresholds, reranker toggle)
- [ ] 13.3 Write runbook for common failures (SPLADE down, Neo4j vector index slow, reranker timeout)
