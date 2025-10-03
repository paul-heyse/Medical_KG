## Title

Refactoring Ingestion TypedDict Definitions for Enhanced Type Safety

## Author

TBD

## Reviewers

- TBD
- TBD

## Project Summary

Ingestion adapters currently rely on a monolithic `DocumentRaw` union that attempts to describe every payload shape across terminology, literature, clinical, and guideline sources. The union invites pervasive casting, obscures required versus optional keys, and causes noisy `mypy` output. This proposal refactors those definitions by extracting common mixins, introducing adapter-specific `TypedDict` aliases, and tightening annotations so that ingestion payloads are explicit, reusable, and enforceable at the type level.

## Goals

- Reduce redundancy across ingestion payload definitions by sharing common base mixins.
- Improve readability and maintainability of adapter implementations by using precise `TypedDict` aliases.
- Enhance type safety so `mypy --strict` can detect schema mismatches earlier in development.

## Requirements

- **Consolidate Common Fields:** Identify shared fields across ingestion payloads and capture them in reusable base `TypedDict` mixins.
- **Explicit Optionality:** Mark optional keys with `NotRequired` (or equivalent) so adapters are explicit about absent data rather than relying on broad `total=False` unions.
- **Adapter-Specific Payloads:** Define dedicated `TypedDict` aliases per adapter family and update adapters to emit those types without ad-hoc casting.
- **Document.raw Type Enforcement:** Update `Document` models and helper utilities so the `raw` attribute references the refined payload union.
- **Tooling Alignment:** Ensure `mypy --strict` and ingestion unit tests pass with the new definitions and adjust documentation accordingly.

## Success Metrics

- Reduction in casting and redundant validation logic inside adapters (qualitative review).
- `mypy --strict src/Medical_KG/ingestion` completes with zero new suppressions.
- Positive reviewer feedback on clarity and maintainability of the new payload structures.

## Participants and Stakeholders

- **Lead:** TBD
- **Implementers:** TBD
- **Reviewers:** TBD, TBD
- **Stakeholders:** Ingestion engineering group, QA

## Implementation Plan

1. **Analysis Phase:** Inventory existing payload usage, identify common fields, and catalogue optional metadata per adapter family.
2. **Refactoring Phase:** Introduce mixins, create adapter-specific payload aliases, and align adapters plus helper utilities with the new types.
3. **Validation Phase:** Run `mypy --strict` and the ingestion test suite, addressing any regressions; gather reviewer feedback.
4. **Documentation Phase:** Update developer docs and communicate the new payload contracts to the team.

## Infrastructure Considerations

No new infrastructure requirements; changes are confined to Python modules and tests.

## Accessibility and Marketing Considerations

Not applicable—this is internal code quality work.
