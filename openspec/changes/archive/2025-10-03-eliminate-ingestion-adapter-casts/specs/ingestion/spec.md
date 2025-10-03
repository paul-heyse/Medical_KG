# Adapter Cast Elimination Delta

## ADDED Requirements

### Requirement: Narrowing Functions for Type Safety

The ingestion system SHALL provide type-safe narrowing functions that explicitly convert `JSONValue` to more specific types with runtime validation, eliminating the need for unsafe `typing.cast()` calls.

#### Scenario: Narrowing function validates and converts

- **WHEN** adapter code needs to narrow a `JSONValue` to `JSONMapping` or `JSONSequence`
- **THEN** a narrowing function SHALL be available that performs runtime type checking
- **AND** the function SHALL raise `TypeError` with context if the value doesn't match the expected type
- **AND** the function SHALL return a properly typed value for static analysis

#### Scenario: Adapters use narrowing instead of cast

- **WHEN** an adapter needs to access nested JSON structures from external APIs
- **THEN** the adapter SHALL use narrowing functions rather than `typing.cast()`
- **AND** casts SHALL be used only at true boundary parsing where external API shape is genuinely unknown

#### Scenario: Cast usage is minimized and documented

- **WHEN** a `typing.cast()` remains necessary in ingestion code
- **THEN** the cast SHALL be documented with an inline comment explaining why narrowing is insufficient
- **AND** the cast SHALL occur only at external API boundary parsing
- **AND** the total number of casts in the ingestion module SHALL be ≤5
