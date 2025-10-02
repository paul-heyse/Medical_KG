# Add Facet Summaries (Per-Chunk Medical Facets)

## Why

Compact, structured facet summaries (≤120 tokens) enable intent-targeted retrieval by providing queryable metadata (PICO, endpoints, AEs, dosing) alongside full chunk text. Facets are indexed separately with higher BM25F boosts, dramatically improving precision for clinical queries while maintaining span-grounding.

## What Changes

- Implement facet routing (detect dominant clinical intent per chunk: pico, endpoint, ae, dose, eligibility, general)
- Create LLM facet generators per type (specialized prompts; strict JSON schemas; ≤120 token budget; span-grounding mandatory)
- Add facet validation (JSON Schema + token counting; drop optional fields to fit budget; never drop evidence_spans)
- Store facets on :Chunk nodes (facet_pico_v1 string, facet_endpoint_v1 string[], facet_ae_v1 string[], facet_dose_v1 string[])
- Index facets in OpenSearch (facet_json field with BM25F boost 1.6; facet_type keyword for filtering)
- Compute facet embeddings (optional; Qwen via vLLM for dense facet retrieval)
- Implement deduplication (keyed by normalized outcome/drug/grade to avoid redundant facets within document)

## Impact

- **Affected specs**: NEW `facet-summaries` capability
- **Affected code**: NEW `/chunker/facets/`, updates to `/kg/writers/`, `/indexing/`
- **Dependencies**: Chunker (produces chunks), vLLM (LLM facet generation + optional embeddings), OpenSearch (facet indexing)
- **Downstream**: Retrieval (facet_json field boost improves precision); Extraction (facets seed extractors); APIs (expose facets in responses)
- **Quality**: Facets must have ≥1 evidence_span; token budget ≤120 enforced
