# Retrieval Capability

## ADDED Requirements

### Requirement: Multi-Retriever Fusion

The system SHALL combine BM25 (lexical), SPLADE (learned sparse), and Dense (Qwen) retrievers using weighted fusion for robust medical document retrieval.

#### Scenario: Three-way fusion

- **WHEN** query="Does sacubitril/valsartan reduce cardiovascular mortality in HFrEF?"
- **THEN** the system SHALL run BM25, SPLADE, and Dense retrievers in parallel and combine via weighted_fusion(w_bm25=0.30, w_splade=0.35, w_dense=0.35)

#### Scenario: Configurable weights

- **WHEN** config.yaml specifies retrieval.fusion.weights={bm25:0.25, splade:0.40, dense:0.35}
- **THEN** the system SHALL apply these weights and verify sum=1.0±0.01

#### Scenario: RRF fallback

- **WHEN** weighted fusion produces ties or config.retrieval.fusion.method="rrf"
- **THEN** the system SHALL apply reciprocal rank fusion with k=60

### Requirement: BM25 Lexical Retrieval

The system SHALL provide BM25 retrieval over chunk text with boosted fields for medical terminology.

#### Scenario: BM25 query

- **WHEN** searching "enalapril adverse events"
- **THEN** the system SHALL query OpenSearch chunks_v1 index with multi_match on text^1.0, title_path^1.4, facet_json^1.6, table_lines^1.2

#### Scenario: BM25 parameters

- **WHEN** executing BM25
- **THEN** the system SHALL use k1=1.2, b=0.75 (default OpenSearch settings) unless overridden in config

#### Scenario: Top-K retrieval

- **WHEN** topK=20 specified
- **THEN** the system SHALL return top 20 chunks ranked by BM25 score

### Requirement: SPLADE Sparse Retrieval

The system SHALL perform learned sparse retrieval using SPLADE term expansions with query-side and doc-side matching.

#### Scenario: SPLADE query expansion

- **WHEN** query="heart attack treatment"
- **THEN** the system SHALL expand via SPLADE model to include related terms (e.g., "myocardial", "infarction", "reperfusion") with weights

#### Scenario: SPLADE doc-side matching

- **WHEN** searching with expanded query
- **THEN** the system SHALL match against Chunk.splade_terms[] field in OpenSearch using BM25F with term weights

#### Scenario: SPLADE score normalization

- **WHEN** combining SPLADE scores with other retrievers
- **THEN** the system SHALL normalize SPLADE scores to [0,1] range using min-max scaling per result set

### Requirement: Dense Vector Retrieval

The system SHALL perform dense retrieval using Qwen embeddings with cosine similarity via Neo4j or OpenSearch vector search.

#### Scenario: Query embedding

- **WHEN** query="Does metformin prevent diabetes in prediabetic patients?"
- **THEN** the system SHALL embed query via Qwen vLLM service producing 4096-D vector

#### Scenario: Neo4j vector search

- **WHEN** using Neo4j backend
- **THEN** the system SHALL query chunk_qwen_idx vector index with COSINE similarity and return top-K

#### Scenario: OpenSearch kNN search

- **WHEN** using OpenSearch backend
- **THEN** the system SHALL use knn query on chunk_embedding_qwen field with cosine similarity

### Requirement: Intent-Aware Routing

The system SHALL detect query intent and route to optimized retrieval strategies per intent type.

#### Scenario: Endpoint intent

- **WHEN** query contains "HR", "hazard ratio", "reduce mortality", or similar effect terms
- **THEN** the system SHALL set intent="endpoint" and boost facet_type:endpoint chunks

#### Scenario: Adverse event intent

- **WHEN** query contains "adverse", "side effects", "toxicity", "grade", or AE terms
- **THEN** the system SHALL set intent="ae" and boost section:adverse_reactions chunks

#### Scenario: Eligibility intent

- **WHEN** query contains "eligible", "inclusion", "exclusion", "criteria"
- **THEN** the system SHALL set intent="eligibility" and filter to ClinicalTrials.gov documents

### Requirement: Optional Reranking

The system SHALL optionally apply neural reranker to top-N fusion results for final ranking.

#### Scenario: Reranker enabled

- **WHEN** config.retrieval.reranker.enabled=true
- **THEN** the system SHALL take top-100 fusion results and rerank using cross-encoder model (MedCPT or ms-marco-MiniLM)

#### Scenario: Reranker topN

- **WHEN** reranking
- **THEN** the system SHALL rerank top-N=100 candidates and return top-K=20 after reranking

#### Scenario: Reranker disabled

- **WHEN** config.retrieval.reranker.enabled=false or P95 latency exceeds SLO
- **THEN** the system SHALL skip reranking and return fusion results directly

### Requirement: Neighbor Merging

The system SHALL merge overlapping chunks when they appear in top results to reduce redundancy.

#### Scenario: Detect overlaps

- **WHEN** top results include chunks with OVERLAPS edges
- **THEN** the system SHALL identify overlapping chunks via Neo4j traversal

#### Scenario: Merge decision

- **WHEN** two chunks overlap and cosine(chunk1, chunk2) > min_cosine (0.85)
- **THEN** the system SHALL merge into single result with combined_text (deduplicated) and max(score1, score2)

#### Scenario: Token budget limit

- **WHEN** merged chunks exceed max_tokens (800)
- **THEN** the system SHALL keep highest-scoring chunk and drop overlapping lower-scoring chunk

### Requirement: Multi-Granularity Retrieval

The system SHALL support retrieval at chunk, facet, and document levels with configurable granularity.

#### Scenario: Chunk-level retrieval

- **WHEN** granularity="chunk" (default)
- **THEN** the system SHALL search chunks_v1 index and return individual chunk results

#### Scenario: Facet-level retrieval

- **WHEN** granularity="facet" and query has clinical intent
- **THEN** the system SHALL search facets with boosted facet_json field and return facet-enriched chunks

#### Scenario: Document-level aggregation

- **WHEN** granularity="document"
- **THEN** the system SHALL aggregate chunk scores per doc_id and return top documents with best chunks highlighted

### Requirement: Filter Support

The system SHALL support filtering by source, date range, section, intent, and document type.

#### Scenario: Source filter

- **WHEN** query with filter={source: ["clinicaltrials", "pmc"]}
- **THEN** the system SHALL add terms filter on Chunk.doc_id prefix

#### Scenario: Date range filter

- **WHEN** query with filter={date_range: {gte: "2020-01-01", lte: "2023-12-31"}}
- **THEN** the system SHALL filter on Document.publication_date

#### Scenario: Section filter

- **WHEN** query with filter={section: ["methods", "results"]}
- **THEN** the system SHALL filter on Chunk.section field

### Requirement: Query Metadata and Explain

The system SHALL return query metadata including component scores, retrieval times, and optional explain mode.

#### Scenario: Component scores

- **WHEN** fusion retrieval completes
- **THEN** the system SHALL return query_meta including bm25_score, splade_score, dense_score, final_score per result

#### Scenario: Retrieval timing

- **WHEN** query executes
- **THEN** the system SHALL return timing breakdown: {bm25_ms, splade_ms, dense_ms, fusion_ms, rerank_ms, total_ms}

#### Scenario: Explain mode

- **WHEN** query includes explain=true
- **THEN** the system SHALL return detailed scoring explanation including term matches, vector similarities, and fusion weights applied

### Requirement: API Endpoint

The system SHALL provide POST /retrieve endpoint accepting structured queries and returning ranked results.

#### Scenario: Retrieve request

- **WHEN** POST /retrieve with {query, intent?, filters?, topK?, rerank_enabled?}
- **THEN** the system SHALL execute fusion retrieval and return {results[], query_meta}

#### Scenario: Result format

- **WHEN** returning results
- **THEN** each result SHALL include {chunk_id, doc_id, text, title_path, section, intent, scores{bm25, splade, dense, final}, start, end}

#### Scenario: Pagination

- **WHEN** requesting more results
- **THEN** the system SHALL support from/size pagination with consistent ordering

### Requirement: Monitoring and Metrics

The system SHALL emit retrieval metrics for performance monitoring and quality tracking.

#### Scenario: Latency tracking

- **WHEN** retrieval queries execute
- **THEN** the system SHALL emit retrieve_duration_seconds_bucket{component: bm25|splade|dense|fusion|rerank}

#### Scenario: Retriever contributions

- **WHEN** fusion combines retrievers
- **THEN** the system SHALL emit component_contribution_pct{retriever} showing % of top-K results from each retriever

#### Scenario: Cache hit rate

- **WHEN** query cache is enabled
- **THEN** the system SHALL emit retrieve_cache_hit_rate, retrieve_cache_hits_total, retrieve_cache_misses_total
