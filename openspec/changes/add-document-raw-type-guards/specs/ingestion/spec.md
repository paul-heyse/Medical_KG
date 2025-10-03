# Document.raw Type Guards Delta

## ADDED Requirements

### Requirement: Type Guard Functions for Payload Narrowing

The ingestion system SHALL provide type guard functions that enable static type checkers to narrow `DocumentRaw` unions to specific payload types, eliminating the need for runtime `isinstance` checks.

#### Scenario: Type guard narrows union type

- **WHEN** code needs to verify a `DocumentRaw` instance matches a specific payload family
- **THEN** a type guard function SHALL be available that returns `TypeGuard[SpecificPayloadType]`
- **AND** the type guard SHALL enable static type checkers to narrow the type within the guarded scope

#### Scenario: Type guard defined for each payload family

- **WHEN** the ingestion system defines payload family unions (terminology, literature, clinical, guidelines, knowledge base)
- **THEN** a corresponding type guard function SHALL exist for each family union
- **AND** the type guard SHALL check that the payload belongs to that family's constituent types

#### Scenario: Adapter validation uses type guards

- **WHEN** an adapter's `validate()` method needs to access `document.raw` fields
- **THEN** the method SHALL use a type guard to narrow the payload type
- **AND** the method SHALL NOT use `isinstance(document.raw, Mapping)` checks for type narrowing

#### Scenario: Type guard handles None payloads

- **WHEN** a type guard is called with `document.raw` that may be `None`
- **THEN** the type guard SHALL safely return `False` for `None` values
- **AND** shall not raise exceptions for null payloads
