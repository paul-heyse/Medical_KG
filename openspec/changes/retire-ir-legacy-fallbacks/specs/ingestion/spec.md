# Spec Delta: IR Layer (retire-ir-legacy-fallbacks)

## REMOVED Requirements

### Requirement: Optional Raw Payload Support

**Reason**: All adapters now provide typed payloads after TypedDict integration

**Migration**: Ensure all `Document` instances have typed `raw` field populated

The IR builder previously accepted documents with missing or untyped `raw` payloads and synthesized placeholder values.

### Requirement: Fallback Payload Coercion

**Reason**: Type-safe flow eliminates need for defensive coercion

**Migration**: Use typed `DocumentRaw` union types for all document construction

Fallback coercion included placeholder synthesis, empty dict defaults, and string-to-mapping conversions.

## ADDED Requirements

### Requirement: Typed Raw Payload Enforcement

The IR builder SHALL require `Document.raw` to be a valid member of the `DocumentRaw` union type.

#### Scenario: Build IR from typed payload

- **GIVEN** a `Document` with typed `raw` payload (e.g., `PubMedDocumentPayload`)
- **WHEN** `DocumentIRBuilder.build()` is called
- **THEN** IR nodes are constructed using typed field access
- **AND** metadata is extracted without runtime coercion
- **AND** mypy validates the payload structure at compile time

#### Scenario: Reject document without raw payload

- **GIVEN** a `Document` instance with `raw=None`
- **WHEN** the document is passed to IR builder
- **THEN** a `ValueError` is raised immediately
- **AND** the error message indicates `raw` field is required
- **AND** the error suggests using typed adapter payloads

#### Scenario: Reject document with untyped raw

- **GIVEN** a `Document` with `raw` as plain dict (not TypedDict)
- **WHEN** mypy type checking is performed
- **THEN** a type error is reported
- **AND** the error indicates `DocumentRaw` union is required

## MODIFIED Requirements

### Requirement: IR Node Construction

The IR builder SHALL construct nodes using type-safe field access from typed payloads.

**Modifications**:

- Removed fallback coercion and placeholder synthesis
- Added compile-time type validation for payload structure
- Enabled structured metadata extraction

#### Scenario: Extract metadata from typed payload

- **GIVEN** a `Document` with `PubMedDocumentPayload` as raw
- **WHEN** IR builder extracts metadata
- **THEN** `raw["pmid"]` accesses the typed field
- **AND** mypy verifies the field exists at compile time
- **AND** no runtime dict lookup failures occur

#### Scenario: Extract version information

- **GIVEN** a document with a payload implementing `VersionMixin`
- **WHEN** version metadata is extracted
- **THEN** the `version` field is accessed type-safely
- **AND** the version string is present (or explicitly `NotRequired`)
- **AND** no coercion from missing values is performed

### Requirement: IR Validation

The IR validator SHALL enforce typed payload requirements during validation.

**Modifications**:

- Added validation for required TypedDict fields
- Removed fallback validation for missing raw payloads

#### Scenario: Validate document with typed payload

- **GIVEN** a `Document` with properly typed raw payload
- **WHEN** `validate_document_ir()` is called
- **THEN** validation checks required TypedDict fields
- **AND** validation passes for well-formed payloads
- **AND** clear error messages indicate any missing fields

#### Scenario: Validation fails for malformed payload

- **GIVEN** a document with raw payload missing required fields
- **WHEN** validation is performed
- **THEN** a `ValidationError` is raised
- **AND** the error specifies which required fields are missing
- **AND** the payload type is included in the error message
