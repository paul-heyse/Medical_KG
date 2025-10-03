# Implementation Tasks

## 1. Audit Current Documentation

- [x] 1.1 Review `docs/ingestion_runbooks.md` for HTTP client usage examples
- [x] 1.2 Identify all instances of old client patterns (direct subscripting)
- [x] 1.3 Check `docs/operations_manual.md` for HTTP client references
- [x] 1.4 List all code examples that need updating

## 2. Update HTTP Client Usage Examples

- [x] 2.1 Replace `data = response["key"]` with `data = response.data["key"]`
- [x] 2.2 Replace `text = response` with `text = response.text`
- [x] 2.3 Replace `content = response` with `content = response.content`
- [x] 2.4 Update all adapter examples to use typed responses
- [x] 2.5 Update runbook failure scenarios with correct response access

## 3. Add HTTP Client Response Types Section

- [x] 3.1 Create "HTTP Client Response Types" section in ingestion_runbooks.md
- [x] 3.2 Document `JsonResponse` class with attributes and usage
- [x] 3.3 Document `TextResponse` class with attributes and usage
- [x] 3.4 Document `BytesResponse` class with attributes and usage
- [x] 3.5 Add code examples for each response type
- [x] 3.6 Explain when each type is returned (get_json vs get_text vs get_bytes)

## 4. Add Integration Examples

- [x] 4.1 Show complete adapter example using typed responses + TypedDict
- [x] 4.2 Demonstrate error handling with response wrappers
- [x] 4.3 Show async iteration patterns with typed responses
- [x] 4.4 Link to `docs/type_safety.md` for detailed patterns

## 5. Add Troubleshooting Section

- [x] 5.1 Document "JsonResponse object is not subscriptable" error
- [x] 5.2 Document "TextResponse has no attribute 'strip'" error
- [x] 5.3 Add migration guide from old to new client usage
- [x] 5.4 Provide quick reference table (old pattern → new pattern)

## 6. Cross-Reference Documentation

- [x] 6.1 Link to `docs/ingestion_typed_contracts.md` for TypedDict usage
- [x] 6.2 Link to `docs/type_safety.md` for HTTP client patterns
- [x] 6.3 Reference `src/Medical_KG/ingestion/http_client.py` for implementation
- [x] 6.4 Update README if it references HTTP client usage

## 7. Validation

- [x] 7.1 Verify all code examples are syntactically correct
- [x] 7.2 Test code examples with mypy --strict
- [ ] 7.3 Have operations team review for clarity
- [ ] 7.4 Ensure on-call engineers can follow updated runbook
