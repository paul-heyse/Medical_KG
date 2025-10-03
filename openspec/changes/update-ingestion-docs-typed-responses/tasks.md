# Implementation Tasks

## 1. Audit Current Documentation

- [ ] 1.1 Review `docs/ingestion_runbooks.md` for HTTP client usage examples
- [ ] 1.2 Identify all instances of old client patterns (direct subscripting)
- [ ] 1.3 Check `docs/operations_manual.md` for HTTP client references
- [ ] 1.4 List all code examples that need updating

## 2. Update HTTP Client Usage Examples

- [ ] 2.1 Replace `data = response["key"]` with `data = response.data["key"]`
- [ ] 2.2 Replace `text = response` with `text = response.text`
- [ ] 2.3 Replace `content = response` with `content = response.content`
- [ ] 2.4 Update all adapter examples to use typed responses
- [ ] 2.5 Update runbook failure scenarios with correct response access

## 3. Add HTTP Client Response Types Section

- [ ] 3.1 Create "HTTP Client Response Types" section in ingestion_runbooks.md
- [ ] 3.2 Document `JsonResponse` class with attributes and usage
- [ ] 3.3 Document `TextResponse` class with attributes and usage
- [ ] 3.4 Document `BytesResponse` class with attributes and usage
- [ ] 3.5 Add code examples for each response type
- [ ] 3.6 Explain when each type is returned (get_json vs get_text vs get_bytes)

## 4. Add Integration Examples

- [ ] 4.1 Show complete adapter example using typed responses + TypedDict
- [ ] 4.2 Demonstrate error handling with response wrappers
- [ ] 4.3 Show async iteration patterns with typed responses
- [ ] 4.4 Link to `docs/type_safety.md` for detailed patterns

## 5. Add Troubleshooting Section

- [ ] 5.1 Document "JsonResponse object is not subscriptable" error
- [ ] 5.2 Document "TextResponse has no attribute 'strip'" error
- [ ] 5.3 Add migration guide from old to new client usage
- [ ] 5.4 Provide quick reference table (old pattern → new pattern)

## 6. Cross-Reference Documentation

- [ ] 6.1 Link to `docs/ingestion_typed_contracts.md` for TypedDict usage
- [ ] 6.2 Link to `docs/type_safety.md` for HTTP client patterns
- [ ] 6.3 Reference `src/Medical_KG/ingestion/http_client.py` for implementation
- [ ] 6.4 Update README if it references HTTP client usage

## 7. Validation

- [ ] 7.1 Verify all code examples are syntactically correct
- [ ] 7.2 Test code examples with mypy --strict
- [ ] 7.3 Have operations team review for clarity
- [ ] 7.4 Ensure on-call engineers can follow updated runbook
