# Semantic Chunking Profiles

## Domain Profiles

- **IMRaD**: 450-token target, 15% overlap, coherence threshold 0.72. Use for journal articles (PMC source systems).
- **Registry**: 350-token target, overlap 20%, coherence threshold 0.70. Optimised for structured criteria blocks.
- **Structured Product Label (SPL)**: 300-token target, overlap 18%, hard boundaries on LOINC-driven sections.
- **Guideline**: 500-token target, 12% overlap, tolerant coherence threshold 0.65 to support narrative recommendations.

Profiles are selected automatically from document metadata (`source_system`, `media_type`). Override by passing a `ChunkingProfile` into `ChunkingPipeline.run` when bespoke tuning is required.

## Tuning Guidance

- **Target Tokens**: Increase for narrative-heavy corpora or when coherence is consistently >0.85. Decrease for data-dense lab reports.
- **Tau Coherence**: Raising the threshold shortens chunks and yields crisper boundaries; lower values produce longer segments at the expense of topical purity.
- **Overlap Tokens**: 10–20% balances retrieval recall with indexing cost. Increase when downstream QA requires more context continuity.
- **Embedding Client**: The chunker uses Qwen embeddings to modulate coherence. Adjust `SemanticChunker.embedding_client.batch_size` to fit GPU memory.

## Fallback Strategies

1. **Multi-Granularity Indexing** – use `ChunkIndexer` to emit chunk-, paragraph-, and section-level documents. Combine with reciprocal rank fusion for blended retrieval.
2. **Sliding Windows** – for problematic documents, configure 512/768 token windows with 25% overlap via the indexer to supplement semantic chunks.
3. **Neighbor Merge** – at query time, merge adjacent chunks when cosine similarity ≥0.60; the helper `ChunkIndexer.neighbor_merge` surfaces eligible pairs.
