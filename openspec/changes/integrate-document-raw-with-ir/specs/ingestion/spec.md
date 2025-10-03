# IR Integration Delta (Ingestion Spec)

## ADDED Requirements

### Requirement: IR Layer Payload Integration

The ingestion system SHALL provide typed payloads that enable IR construction components to extract structured metadata and blocks type-safely, without requiring JSON re-parsing or string manipulation.

#### Scenario: Document.raw flows to IR builder

- **WHEN** a `Document` with typed `raw` payload is passed to IR construction
- **THEN** the IR builder SHALL accept the `raw` payload as an optional parameter
- **AND** the IR builder MAY extract source-specific structure (sections, metadata) from the typed payload

#### Scenario: Payload extraction is type-safe

- **WHEN** the IR builder processes a typed payload
- **THEN** the extraction logic SHALL leverage TypedDict field access without casting
- **AND** mypy SHALL verify that extracted fields match expected types

#### Scenario: IR construction works without payloads

- **WHEN** IR builder is called without a typed payload (backward compatibility)
- **THEN** IR construction SHALL complete successfully using generic metadata
- **AND** no structural extraction from payloads SHALL be attempted
