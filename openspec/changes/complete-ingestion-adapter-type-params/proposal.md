# Complete Ingestion Adapter Type Parameterization

## Why

5 terminology adapters (`MeSHAdapter`, `UMLSAdapter`, `LoincAdapter`, `Icd11Adapter`, `SnomedAdapter`) and 3 literature adapters (`PubMedAdapter`, `PmcAdapter`, `MedRxivAdapter`) currently inherit from `HttpAdapter` without specifying `Generic[RawPayloadT]` type parameters. This causes ~70 mypy strict mode errors (10 type-arg, 10 arg-type, ~50 union-attr) and prevents compile-time payload validation. These adapters cannot leverage the TypedDict payload contracts introduced in `refactor-ingestion-typedicts`.

## What Changes

- Parameterize 5 terminology adapters with their respective TypedDict types from `ingestion/types.py`
- Parameterize 3 literature adapters with `PubMedDocumentPayload`, `PmcDocumentPayload`, `MedRxivDocumentPayload`
- Update all `parse(raw: Any)` signatures to `parse(raw: SpecificPayload)` with proper type annotations
- Replace dict literal construction in `parse()` methods with properly typed TypedDict assignments
- Remove `Any` types from fetch() return signatures where applicable

## Impact

- **Affected specs**: `ingestion` (via delta modifying Typed Payload Contracts requirement)
- **Affected code**:
  - `src/Medical_KG/ingestion/adapters/terminology.py` (~250 lines, 5 adapters)
  - `src/Medical_KG/ingestion/adapters/literature.py` (~450 lines, 3 adapters)
  - `tests/ingestion/test_adapters.py` (type assertion updates)
  - `tests/ingestion/fixtures/*.py` (ensure fixtures match TypedDict schemas)
- **Resolves**: ~70 mypy errors, unblocks all downstream type safety work
- **Coordination**: Must complete before `update-type-safety-ingestion-base` to avoid merge conflicts
