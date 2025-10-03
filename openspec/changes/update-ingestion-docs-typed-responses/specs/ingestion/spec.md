# Ingestion Documentation Update for Typed Responses

## ADDED Requirements

### Requirement: HTTP Client Response Type Documentation

The ingestion system documentation SHALL explain the typed response wrapper objects returned by the HTTP client, including their attributes and proper usage patterns.

#### Scenario: JsonResponse documentation

- **WHEN** a developer reads ingestion documentation for HTTP client usage
- **THEN** documentation SHALL explain JsonResponse has `.data`, `.url`, `.status_code` attributes
- **AND** SHALL show examples of accessing JSON data via `.data` attribute
- **AND** SHALL NOT show deprecated patterns like direct subscripting of response

#### Scenario: Migration guidance provided

- **WHEN** a developer encounters "object is not subscriptable" error
- **THEN** documentation SHALL provide troubleshooting section explaining the error
- **AND** SHALL show migration from `response["key"]` to `response.data["key"]`
- **AND** SHALL link to HTTP client implementation for full API reference

#### Scenario: Runbook examples are type-safe

- **WHEN** an on-call engineer follows runbook HTTP client examples
- **THEN** all code examples SHALL pass mypy --strict without errors
- **AND** SHALL use correct response wrapper attributes (`.data`, `.text`, `.content`)
- **AND** SHALL integrate with TypedDict payload patterns where applicable
