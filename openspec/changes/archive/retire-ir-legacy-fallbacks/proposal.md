# Proposal: Retire IR Layer Legacy Fallbacks

## Why

The IR (Intermediate Representation) builder currently accepts `Document` instances with untyped or missing `raw` payloads and synthesizes placeholder values for backwards compatibility. After completing the typed payload follow-up work (all 7 TypedDict proposals), this fallback behavior prevents leveraging structured metadata downstream and maintains unnecessary coercion paths. Requiring typed payloads enforces the typed contract end-to-end and enables compile-time verification of payload structure.

## What Changes

- **Require typed raw payloads**: Make `Document.raw` a required field with typed union
- **Delete fallback coercion**: Remove placeholder synthesis in `DocumentIRBuilder`
- **Update adapter integrations**: Ensure all adapters pass typed payloads to IR
- **Add strict mypy enforcement**: Enable strict type checking for IR builder inputs
- **Remove legacy behavior documentation**: Delete references to "optional raw" payloads
- **Update IR tests**: Rewrite tests to use typed payloads exclusively

## Impact

**Affected specs**: `ingestion` (IR layer), `extraction` (downstream consumers)

**Affected code**:

- `src/Medical_KG/ir/builder.py` - Remove fallback coercion (~40 lines)
- `src/Medical_KG/ir/validator.py` - Update validation to expect typed payloads
- `src/Medical_KG/ingestion/adapters/` - Ensure all adapters provide typed payloads
- `tests/ir/test_builder.py` - Rewrite tests for typed payloads (~60 lines)
- `docs/ir_pipeline.md` - Remove legacy behavior documentation

**Breaking Change**: YES - removes fallback coercion for missing/untyped raw payloads

**Migration Path**: All adapters must provide typed `Document.raw` payloads (already done after TypedDict work)

**Benefits**:

- Type-safe Document→IR flow enforced at compile time
- Eliminates runtime coercion overhead
- Enables structured metadata extraction in IR layer
- -80 lines of defensive fallback code removed
- mypy strict compliance for IR module
- Clearer error messages when payloads are malformed
