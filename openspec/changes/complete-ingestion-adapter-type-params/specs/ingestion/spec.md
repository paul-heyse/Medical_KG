# Ingestion Adapter Type Parameterization Delta

## MODIFIED Requirements

### Requirement: Typed Payload Contracts

The ingestion system SHALL define explicit, adapter-scoped payload contracts that describe required and optional fields without relying on a monolithic union. All adapters MUST declare their payload type parameter when inheriting from `BaseAdapter` or `HttpAdapter`.

#### Scenario: Adapter declares type parameter

- **WHEN** an ingestion adapter class is defined
- **THEN** the adapter SHALL inherit from `BaseAdapter[SpecificPayloadType]` or `HttpAdapter[SpecificPayloadType]` with an explicit TypedDict type parameter
- **AND** the type parameter SHALL correspond to a payload TypedDict defined in `ingestion/types.py`

#### Scenario: Adapter payload schema is defined

- **WHEN** an ingestion adapter serializes a document
- **THEN** the serialized payload SHALL conform to that adapter's dedicated `TypedDict` alias without using `typing.cast` to satisfy the type checker

#### Scenario: Shared fields reuse common mixins

- **WHEN** multiple adapter payloads reuse the same fields (e.g., identifiers or versions)
- **THEN** those fields SHALL be declared via reusable mixin `TypedDict`s that each adapter payload inherits

#### Scenario: Optional fields declared explicitly

- **WHEN** an adapter payload includes optional metadata
- **THEN** those fields SHALL be marked using `NotRequired` (or an equivalent explicit optional marker) instead of relying on `total=False` unions

#### Scenario: Document.raw type safety enforced

- **WHEN** a `Document` exposes its raw payload
- **THEN** the `raw` attribute SHALL reference the refined payload union so static analysis can detect schema mismatches

#### Scenario: Parse method signature is typed

- **WHEN** an adapter implements the `parse()` method
- **THEN** the method signature SHALL be `parse(self, raw: SpecificPayloadType) -> Document` where `SpecificPayloadType` matches the adapter's type parameter
- **AND** the implementation SHALL construct the payload as a properly typed TypedDict instance
