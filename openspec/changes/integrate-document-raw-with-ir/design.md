# IR Integration with Typed Payloads - Design

## Context

The ingestion layer has TypedDict contracts for adapter payloads, but the IR layer treats all metadata as `Mapping[str, Any]`. This creates a discontinuity where typed information becomes untyped at the IR boundary. The IR builder could extract richer structure if it understood payload types.

## Goals

- Enable type-safe extraction of structured metadata from typed payloads into IR
- Maintain backward compatibility with existing IR construction that doesn't use payloads
- Provide foundation for source-specific IR enrichment (e.g., clinical trial sections as blocks)
- Keep IR layer agnostic to ingestion details (loose coupling)

## Non-Goals

- Mandatory payload usage (IR should work without typed payloads for backward compatibility)
- Runtime payload validation in IR (validation remains in ingestion layer)
- Deep ingestion/IR coupling (IR imports from ingestion/types but doesn't depend on adapters)

## Decisions

### Decision 1: Optional Payload Parameter in IrBuilder.build()

**Chosen**: Add `raw: AdapterDocumentPayload | None = None` parameter to `IrBuilder.build()`

**Rationale**:

- Backward compatible: existing calls without `raw` continue working
- Explicit opt-in: callers must pass payload to enable enrichment
- Type-safe: mypy can verify payload matches expected structure

**Alternatives Considered**:

- Store payload in metadata dict: Loses type safety, requires casting in IR
- Require payload always: Breaking change for existing code
- Implicit payload via Document reference: Couples IR to ingestion Document model

### Decision 2: Payload-Specific Extractor Functions

**Chosen**: Create `_extract_from_literature()`, `_extract_from_clinical()`, etc. methods in `IrBuilder`

**Rationale**:

- Single responsibility: each extractor handles one payload family
- Testable: can unit test extractors independently
- Extensible: new payload families add new extractors without modifying core logic

**Alternatives Considered**:

- Visitor pattern: Over-engineered for this scale
- Match/case on payload type: Couples IR to all payload types
- Protocol-based: Payloads don't need common interface currently

### Decision 3: IR Imports from ingestion/types

**Chosen**: `ir/builder.py` imports `AdapterDocumentPayload` union from `ingestion/types`

**Rationale**:

- Clear dependency: IR depends on ingestion types (acceptable layering)
- Avoids duplication: Single source of truth for payload schemas
- Type hints work: mypy can verify across module boundaries

**Alternatives Considered**:

- Duplicate types in IR: Violates DRY, causes drift
- Protocol/interface layer: Unnecessary abstraction at this scale
- Avoid imports: Lose type safety, requires Any

## Implementation Plan

### Phase 1: Add Optional Parameter

1. Update `IrBuilder.build()` signature with `raw: AdapterDocumentPayload | None = None`
2. Add conditional logic: if raw is not None, route to payload extractors
3. Verify backward compatibility: all existing tests pass without changes

### Phase 2: Implement Extractors

1. Implement `_extract_from_literature(raw: LiteratureDocumentPayload)`:
   - PMC sections → IR blocks with section metadata
   - PubMed MeSH terms → provenance metadata
2. Implement `_extract_from_clinical(raw: ClinicalCatalogDocumentPayload)`:
   - Trial arms → structured blocks
   - Eligibility criteria → metadata
3. Implement `_extract_from_guidelines(raw: GuidelineDocumentPayload)`:
   - Recommendations → annotated blocks

### Phase 3: Integration Testing

1. Test Document→DocumentIR flow with typed payloads for each adapter family
2. Test backward compatibility: IR works without payloads
3. Test that extracted blocks validate correctly

## Risks & Trade-offs

### Risk: IR becomes too coupled to ingestion

- **Mitigation**: IR only imports type unions, not adapter implementations
- **Acceptance**: Some coupling acceptable as IR naturally depends on data sources

### Risk: Payload extractors drift from adapter implementations

- **Mitigation**: Integration tests verify Document→IR flow for each adapter
- **Acceptance**: Extractors focus on subset of fields, not full payload

### Trade-off: Performance overhead of payload dispatch

- **Impact**: Type checking and dispatch adds ~10% overhead to IR construction
- **Justification**: Type safety and structured extraction worth the cost
- **Opt-out**: Callers can omit payload to skip overhead

## Migration Plan

### For Existing Code

- No changes required: existing `IrBuilder.build()` calls work without payload
- Optional enhancement: pass `raw=document.raw` to enable structured extraction

### For New Code

- Encouraged pattern: always pass `raw=document.raw` when available
- Code review checklist: verify IR construction uses typed payloads where applicable

## Open Questions

1. **Should DocumentIR store a reference to source payload?**
   - Pro: Enables downstream consumers to access typed source data
   - Con: Increases memory footprint, couples IR to ingestion schemas
   - **Proposed**: Defer until use case emerges

2. **Should payload extractors be pluggable/registry-based?**
   - Pro: Extensible for custom adapter families
   - Con: Adds complexity, no current need for third-party adapters
   - **Proposed**: Use simple if/elif dispatch initially, refactor if needed

3. **Should IR validation differ based on payload type?**
   - Pro: Source-specific validation rules (e.g., clinical trials need NCT ID in metadata)
   - Con: Adds complexity to validator
   - **Proposed**: Add optional payload-aware validation in Phase 2, keep basic validation always
