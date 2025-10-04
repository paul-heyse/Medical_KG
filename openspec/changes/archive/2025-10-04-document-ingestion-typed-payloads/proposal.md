# Document Ingestion Typed Payload Contracts

## Why

New contributors need clear guidance on how to work with TypedDict payload contracts when creating or modifying ingestion adapters. Current documentation doesn't explain:

- How to define adapter-specific TypedDicts using mixins
- When to use `NotRequired` vs required fields
- How to write type-safe `parse()` implementations
- How typed payloads flow from adapters through IR to downstream consumers
Without this documentation, developers will revert to `Any` types, miss type safety benefits, and create inconsistent adapter patterns.

## What Changes

- Create comprehensive `docs/ingestion_typed_contracts.md` guide (~300 lines):
  - TypedDict design patterns and mixin inheritance
  - NotRequired field conventions and when to use them
  - Type guard usage examples
  - Complete adapter examples (terminology, literature, clinical)
- Update `docs/ingestion_runbooks.md` (+150 lines):
  - "Adding a New Adapter" section with typed payload scaffolding
  - Migration guide from `Any`-typed to TypedDict adapters
  - Troubleshooting mypy errors in adapters
- Update `CONTRIBUTING.md` (+50 lines):
  - Mandate TypedDict definitions for new adapters
  - Mypy strict compliance checklist
  - Code review checklist for typed adapters
- Add comprehensive module docstrings to `src/Medical_KG/ingestion/types.py` (+100 lines):
  - Document each payload family union and when to use it
  - Explain mixin inheritance patterns with examples
  - Document type guard functions

## Impact

- **Affected specs**: `ingestion` (adds documentation requirement)
- **Affected code**:
  - `docs/ingestion_typed_contracts.md` (new, ~300 lines)
  - `docs/ingestion_runbooks.md` (update, +150 lines)
  - `CONTRIBUTING.md` (update, +50 lines)
  - `src/Medical_KG/ingestion/types.py` (docstrings, +100 lines)
- **Benefits**: Faster contributor onboarding, consistent adapter patterns, fewer type safety violations
- **Target**: Developer can create properly typed adapter in <2 hours following docs
