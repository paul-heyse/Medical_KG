## 1. Type Definition Overhaul

- [ ] 1.1 Catalogue existing ingestion `TypedDict` usage across adapters.
- [ ] 1.2 Introduce shared mixins for common document fields.
- [ ] 1.3 Create adapter-specific payload aliases with explicit required/optional fields.

## 2. Adapter Alignment

- [ ] 2.1 Update terminology adapters to emit the new payloads.
- [ ] 2.2 Refactor literature adapters for the refined payload types.
- [ ] 2.3 Apply the schema to guideline/clinical adapters and normalise raw data handling.

## 3. Validation & Tooling

- [ ] 3.1 Update `Document.raw` typing and helper utilities.
- [ ] 3.2 Run `mypy --strict` for ingestion, ensure zero regressions.
- [ ] 3.3 Refresh ingestion documentation and adapter tests to cover new payload structures.
