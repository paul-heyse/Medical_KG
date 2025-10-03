# Add Semantic Chunking (Medical-Aware)

## Why

Effective retrieval requires chunks that respect clinical boundaries (IMRaD sections, outcome measures, eligibility criteria, SPL LOINC sections) while maintaining semantic coherence. Domain-tuned chunking (target sizes, overlap strategies, intent tagging) dramatically improves retrieval recall and reduces boundary splits.

## What Changes

- Implement domain profiles (IMRaD 600±150 tokens / 15% overlap; Registry 200-700 by section / 15% overlap; SPL 350-550 per LOINC section / 15% overlap; Guidelines 250-500 per recommendation / 10% overlap)
- Add clinical intent tagger (pico_population, pico_intervention, pico_outcome, adverse_event, dose, eligibility, recommendation, lab_value)
- Implement coherence-based boundary detection (cosine similarity threshold τ=0.55 narrative / 0.50 bullets)
- Add hard boundary rules (heading changes, section changes, table start, eligibility kind switch)
- Implement table atomic chunking with LLM table_digest
- Create facet summary generation per chunk (JSON ≤120 tokens; pico/endpoint/ae/dose/eligibility/general types)
- Add neighbor-merge fallback for micro-chunks
- Compute embeddings (Qwen via vLLM) for chunk + facet (GPU-only)

## Impact

- **Affected specs**: NEW `semantic-chunking` capability
- **Affected code**: NEW `/chunker/`, `/chunker/clinical_tagger/`, `/chunker/config/`
- **Dependencies**: IR (input); vLLM (Qwen embeddings for coherence + chunk embeddings); SPLADE (doc expansion)
- **Downstream**: Retrieval (indexes chunks); Extraction (operates on chunks); KG (Chunk nodes)
