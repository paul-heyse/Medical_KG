# Adapter Type Parameterization - Design Document

## Context

The `refactor-ingestion-typedicts` change introduced TypedDict payload contracts in `ingestion/types.py`, but 8 adapters (5 terminology, 3 literature) don't declare type parameters when inheriting from `HttpAdapter[RawPayloadT]`. This causes ~70 mypy errors and prevents compile-time validation of payload structure.

## Goals

- Achieve 100% adapter type parameterization (24/24 adapters properly typed)
- Eliminate ~70 mypy strict mode errors in terminology and literature adapters
- Enable static analysis to catch payload schema mismatches at compile time
- Provide foundation for type-safe validation and processing

## Non-Goals

- Changing adapter runtime behavior (pure type annotation work)
- Introducing runtime payload validation beyond existing patterns
- Refactoring fetch() logic or HTTP client interactions

## Technical Decisions

### Decision 1: Use `Any` as Generic Parameter Initially

**Chosen**: `class MeSHAdapter(HttpAdapter[Any]):`

**Rationale**:

- `fetch()` methods return heterogeneous JSON from external APIs (truly Any)
- Type narrowing happens in `parse()` where raw API response becomes typed payload
- Using specific types for fetch would require upstream API client typing (out of scope)

**Alternatives Considered**:

- `HttpAdapter[MeshDocumentPayload]`: Would require `fetch()` to return typed payloads, but fetch returns raw API JSON
- `HttpAdapter[JSONMapping]`: Too generic, doesn't capture that parse() produces specific TypedDict

### Decision 2: Type parse() Return Value, Not Parameter

**Chosen**: `def parse(self, raw: Any) -> Document:` + typed payload construction inside

**Rationale**:

- `raw` parameter is the untyped API response from `fetch()`
- Type safety happens when constructing the TypedDict payload
- `Document.raw` field is typed, so assignment validates structure

**Example**:

```python
def parse(self, raw: Any) -> Document:
    payload: MeshDocumentPayload = {
        "name": raw.get("descriptor", {}).get("descriptorName", {}).get("string", ""),
        "terms": [t.get("string", "") for t in ...],
        "descriptor_id": raw.get("descriptor", {}).get("descriptorUI"),
    }
    return Document(..., raw=payload)  # mypy validates payload matches DocumentRaw union
```

### Decision 3: Fix Union-Attr Errors with Narrowing Helpers

**Problem**: Literature adapters have ~50 errors like:

```
Item "int" of "JSONValue" has no attribute "get"  [union-attr]
```

**Chosen**: Add narrowing at access points:

```python
search_result = ensure_json_mapping(search.get("esearchresult", {}), context="pubmed search")
webenv = search_result.get("webenv")
```

**Alternatives Considered**:

- Cast to JSONMapping: Unsafe, defeats type checking
- Restructure JSONValue to not include primitives: Breaking change to type system
- Ignore errors: Defeats purpose of type safety initiative

## Implementation Strategy

### Phase 1: Terminology Adapters (Low Complexity)

**Effort**: 2 days
**Adapters**: MeSH, UMLS, LOINC, ICD-11, SNOMED (5 total)

Each adapter follows pattern:

1. Add `[Any]` to class declaration
2. Update `parse()` to construct typed payload
3. Verify Document.raw assignment passes mypy

**Risk**: Low - terminology adapters have simple payloads with few optional fields

### Phase 2: Literature Adapters (High Complexity)

**Effort**: 3-4 days
**Adapters**: PubMed, PMC, MedRxiv (3 total)

Additional challenges:

- PubMed has ~50 union-attr errors from JSONValue narrowing
- PMC has nested structures (sections, media, references)
- All three have many optional fields requiring careful handling

**Risk**: Medium - extensive error fixing required, careful testing needed

### Phase 3: Validation & Integration

**Effort**: 1 day

- Run mypy strict on both files
- Update test fixtures to match schemas
- Integration test Document→IR flow
- Document patterns for future adapters

## Risks & Mitigations

### Risk: Breaking Test Fixtures

- **Impact**: Tests fail if fixtures don't match new TypedDict schemas
- **Mitigation**: Audit fixtures first, ensure all required fields present
- **Acceptance**: Some fixture updates expected and acceptable

### Risk: Runtime Behavior Change

- **Impact**: Typed payloads might expose bugs in validation logic
- **Mitigation**: This is actually a benefit - catching bugs is the goal
- **Rollback**: Pure type annotations can be reverted without runtime impact

### Risk: Union-Attr Errors Proliferate

- **Impact**: Fixing 50 literature errors might reveal more
- **Mitigation**: Systematic narrowing at fetch boundaries addresses root cause
- **Escalation**: If >100 errors appear, consider JSONValue redesign (separate proposal)

## Testing Strategy

### Static Testing

- Mypy strict on modified files
- Confirm error count: ~70 → 0
- No new `# type: ignore` suppressions

### Unit Testing

- Verify existing adapter tests pass unchanged
- Add type assertions for Document.raw
- Test optional field presence/absence

### Integration Testing

- Full ingestion test suite
- Verify Document→IR flow works
- Test with bootstrap data where available

## Success Metrics

- ✅ All 8 adapters declare Generic[RawPayloadT]
- ✅ Mypy strict errors: ~70 → 0
- ✅ Zero new type: ignore comments
- ✅ All tests pass without modification
- ✅ Fixtures updated to match schemas

## Future Work

This change enables:

- Type guards for Document.raw (Proposal 2)
- Elimination of casts and runtime validation (Proposals 3-4)
- IR integration with typed payloads (Proposal 5)

## Open Questions

1. **Should we type the fetch() return value eventually?**
   - Pro: End-to-end type safety from HTTP→Document
   - Con: Requires typing AsyncHttpClient.fetch_json() responses
   - **Decision**: Defer to future work, focus on parse() first

2. **Should JSONValue be refactored to separate primitives?**
   - Pro: Would eliminate many union-attr errors
   - Con: Breaking change to type system, affects multiple modules
   - **Decision**: Handle with narrowing for now, revisit if needed

3. **Should we enforce mypy strict in CI immediately?**
   - Pro: Prevents regression
   - Con: Blocks other work until all errors fixed
   - **Decision**: Add to CI in Proposal 2 after type guards in place
