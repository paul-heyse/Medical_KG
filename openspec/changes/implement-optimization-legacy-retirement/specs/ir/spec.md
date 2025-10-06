## ADDED Requirements
### Requirement: IR Language Normalisation
The IR builder SHALL emit ISO language codes derived from the text normaliser, and the validator SHALL accept only those codes.

#### Scenario: Builder provides language metadata
- **WHEN** `IrBuilder.build` processes a document
- **THEN** `DocumentIR.language` SHALL be a two-letter code provided by `TextNormalizer`

#### Scenario: Validator enforces language codes
- **WHEN** `IRValidator.validate_document` runs on a document
- **THEN** it SHALL reject non-ISO codes with a descriptive error referencing the language field

### Requirement: Metadata Validation Messaging
The IR validator SHALL produce deterministic, actionable error messages for metadata mismatches aligned with updated tests.

#### Scenario: Identifier mismatch message
- **WHEN** metadata identifier differs from the payload value
- **THEN** the validator SHALL raise a `ValidationError` containing the phrase `metadata field 'identifier' must equal`
