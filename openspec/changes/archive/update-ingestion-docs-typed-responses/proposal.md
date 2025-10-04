# Update Ingestion Documentation for Typed Response Wrappers

## Why

The ingestion operations runbook predates the typed response wrapper refactoring (`JsonResponse`, `TextResponse`, `BytesResponse`). Current documentation shows old patterns where HTTP client methods returned raw values, but the system now returns typed wrapper objects with `.data`, `.text`, and `.content` attributes.

On-call engineers and new contributors following the runbook will:

- Write incorrect code that fails type checking
- Be confused by mypy errors about missing subscript operators
- Miss the benefits of type-safe HTTP responses

The recently completed `document-ingestion-typed-payloads` work documented TypedDict contracts but didn't update the operational runbooks for the response wrappers.

## What Changes

- Update `docs/ingestion_runbooks.md` to use typed response wrappers:
  - Replace `response = await client.get_json(url); data = response["key"]`
  - With `response = await client.get_json(url); data = response.data["key"]`
  - Update all examples to use `.data`, `.text`, `.content` attributes

- Add new section "HTTP Client Response Types":
  - Document `JsonResponse` with `.data`, `.url`, `.status_code` attributes
  - Document `TextResponse` with `.text` attribute
  - Document `BytesResponse` with `.content` attribute
  - Explain when each type is returned

- Cross-reference to type safety documentation:
  - Link to `docs/type_safety.md` for HTTP client patterns
  - Reference `docs/ingestion_typed_contracts.md` for payload contracts
  - Show complete example with typed responses + TypedDict payloads

- Add troubleshooting section:
  - Common error: "JsonResponse object is not subscriptable" → use `.data`
  - Common error: "TextResponse object does not support str methods" → use `.text`
  - Migration guide from old client usage to new typed wrappers

## Impact

- **Affected specs**: None (documentation only)
- **Affected code**:
  - `docs/ingestion_runbooks.md` (~80 lines updated + 50 lines new section)
  - Optional: `docs/operations_manual.md` (if it references HTTP client)
- **Benefits**:
  - On-call engineers use correct, type-safe patterns
  - Runbook examples pass mypy --strict
  - Aligned documentation reduces confusion
  - Faster incident resolution (correct patterns documented)
- **Risk**: None (documentation only, no code changes)
