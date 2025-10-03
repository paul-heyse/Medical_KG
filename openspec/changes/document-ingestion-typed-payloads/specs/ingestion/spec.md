# Ingestion Documentation Delta

## ADDED Requirements

### Requirement: Typed Payload Developer Documentation

The ingestion system SHALL provide comprehensive documentation that enables developers to create and maintain typed adapters correctly, including design patterns, examples, and troubleshooting guidance.

#### Scenario: TypedDict patterns are documented

- **WHEN** a developer needs to create a new typed adapter payload
- **THEN** documentation SHALL explain TypedDict design patterns including mixin inheritance
- **AND** documentation SHALL provide examples of properly structured payload TypedDicts
- **AND** documentation SHALL explain when to use `NotRequired` vs required fields

#### Scenario: Complete adapter examples are provided

- **WHEN** a developer needs to implement a new adapter with typed payloads
- **THEN** documentation SHALL include at least 3 complete adapter examples from different families (terminology, literature, clinical)
- **AND** examples SHALL demonstrate fetch(), parse(), and validate() method implementations
- **AND** examples SHALL show how to construct TypedDict payloads correctly

#### Scenario: Type guard usage is explained

- **WHEN** a developer needs to use type guards for payload narrowing
- **THEN** documentation SHALL explain when and how to use type guard functions
- **AND** documentation SHALL provide examples of type guard usage in validation methods

#### Scenario: Migration guidance is available

- **WHEN** a developer needs to convert an existing Any-typed adapter to use TypedDicts
- **THEN** documentation SHALL provide a step-by-step migration guide
- **AND** the guide SHALL explain common mypy errors and how to resolve them

#### Scenario: Contributing requirements enforce typing

- **WHEN** a developer submits a PR adding or modifying an adapter
- **THEN** CONTRIBUTING.md SHALL mandate TypedDict payload definitions
- **AND** SHALL include a mypy strict compliance checklist
- **AND** SHALL reference the typed payload documentation for guidance
