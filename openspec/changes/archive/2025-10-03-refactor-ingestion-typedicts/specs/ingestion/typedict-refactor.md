## MODIFIED Requirements

### Requirement: Typed Payload Contracts

The ingestion system SHALL define explicit, adapter-scoped payload contracts that describe required and optional fields without relying on a monolithic union.

#### Scenario: Adapter payload schema is defined

- **WHEN** an ingestion adapter serializes a document
- **THEN** the serialized payload SHALL conform to that adapter’s dedicated `TypedDict` alias without using `typing.cast` to satisfy the type checker.

#### Scenario: Shared fields reuse common mixins

- **WHEN** multiple adapter payloads reuse the same fields (e.g., identifiers or versions)
- **THEN** those fields SHALL be declared via reusable mixin `TypedDict`s that each adapter payload inherits.

#### Scenario: Optional fields declared explicitly

- **WHEN** an adapter payload includes optional metadata
- **THEN** those fields SHALL be marked using `NotRequired` (or an equivalent explicit optional marker) instead of relying on `total=False` unions.

#### Scenario: Document.raw type safety enforced

- **WHEN** a `Document` exposes its raw payload
- **THEN** the `raw` attribute SHALL reference the refined payload union so static analysis can detect schema mismatches.
