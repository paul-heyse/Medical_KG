# Integrate Typed Document.raw with IR Layer

## Why

The IR layer (`IrBuilder`, `IRValidator`) currently accepts generic `metadata: Mapping[str, Any]` and doesn't leverage typed `Document.raw` payloads. This means structured information available in typed payloads (PMC sections, PubMed MeSH terms, clinical trial outcomes) must be re-parsed from JSON strings or reconstructed, defeating type safety benefits. Integrating typed payloads with IR enables type-safe metadata extraction, structured block generation, and payload-aware validation.

## What Changes

- Extend `IrBuilder.build()` signature to optionally accept `raw: AdapterDocumentPayload | None`
- Create IR payload extractors for each adapter family:
  - Literature: extract sections from PMC payloads as IR blocks, MeSH terms from PubMed as metadata
  - Clinical: extract trial arms, outcomes, eligibility as structured blocks
  - Guidelines: extract recommendations as annotated blocks
- Update `IRValidator` to perform source-specific validation based on payload type
- Add integration tests for Document→DocumentIR transformation with typed payloads
- Maintain backward compatibility: IR builder still works with generic metadata when raw is absent

## Impact

- **Affected specs**: `ingestion`, `ir` (adds IR integration requirement to ingestion, modifies IR spec)
- **Affected code**:
  - `src/Medical_KG/ir/builder.py` (~30 new lines for payload handling)
  - `src/Medical_KG/ir/validator.py` (~20 new lines for payload-aware validation)
  - `src/Medical_KG/ir/models.py` (optional: add `source_payload` field to DocumentIR)
  - `tests/ir/test_builder.py` (new integration tests)
  - `tests/ingestion/test_adapters.py` (verify Document→IR flow)
- **Benefits**: Type-safe IR construction, structured metadata extraction, foundation for source-specific enrichment
- **Risks**: Breaking existing IR workflows if not backward-compatible
- **Coordination**: Should complete after Proposals 1-4 to ensure all payloads are properly typed
