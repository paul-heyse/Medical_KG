# Add Retrieval Fusion (BM25 + SPLADE + Dense)

## Why

Hybrid retrieval combining lexical (BM25), learned sparse (SPLADE-v3), and dense (Qwen) dramatically improves recall and nDCG across medical intents (PICO, endpoints, AEs, dose, eligibility). Fusion strategies (weighted linear, RRF) with optional reranking and neighbor-merge ensure stable, high-quality results.

## What Changes

- Implement three parallel retrievers: BM25/BM25F (OpenSearch), SPLADE-v3 (OpenSearch rank_features), Dense (Neo4j vector KNN)
- Add weighted fusion (default: 0.50 SPLADE + 0.35 dense + 0.15 BM25) with score normalization (min-max to [0,1])
- Implement RRF (Reciprocal Rank Fusion, k=60) as alternative fusion method
- Add optional Qwen reranker (top-100 fused → rerank → final top-K)
- Implement intent routing (PICO/endpoint/ae/dose/eligibility) with per-intent field boosts and filters
- Add ontology-aware query expansion (synonyms from Concept Catalog; BM25 synonyms file; SPLADE inherent expansion)
- Implement neighbor-merge (adjacent chunks with cosine ≥ 0.60; aggregate up to 3000 tokens)
- Add multi-granularity retrieval (paragraph + chunk + section levels; RRF across granularities)
- Create retrieval API (/retrieve with intent, filters, topK, rerank_enabled)

## Impact

- **Affected specs**: NEW `retrieval-fusion` capability
- **Affected code**: NEW `/retrieval/fusion/`, `/retrieval/reranker/`, `/retrieval/intent_router/`
- **Dependencies**: OpenSearch (BM25 + SPLADE indexes), Neo4j (vector index), vLLM (optional reranker), Concept Catalog (synonyms)
- **Downstream**: APIs (expose /retrieve), Briefing Outputs (use retrieval for evidence gathering)
- **SLOs**: P95 latency ≤450ms without rerank, ≤700ms with rerank
