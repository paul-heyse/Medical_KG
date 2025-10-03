# Implementation Tasks

## 1. Model Layer

- [x] 1.1 Convert extraction models to typed BaseModel declarations (explicit field annotations, validators).
- [x] 1.2 Define typed protocols/aliases for span, evidence, and facet cross-links used by extraction outputs.
- [x] 1.3 Update normalizers and parsers to return typed structures without `Any` leakage.

## 2. Service & Metrics

- [x] 2.1 Add type annotations to extraction service entrypoints and helper functions.
- [x] 2.2 Refine metrics calculations to operate on `Sequence`/`Mapping` instead of dynamic attributes.
- [x] 2.3 Ensure KG writer utilities accept typed extraction payloads with validation layers.

## 3. Testing & Validation

- [x] 3.1 Expand unit tests to cover typed models and ensure backwards-compatible serialization.
- [x] 3.2 Run `mypy --strict src/Medical_KG/extraction` and fix all remaining errors.
- [x] 3.3 Execute targeted pytest suite covering extraction services. *(Coverage trace tooling still flags unrelated files; ran with `DISABLE_COVERAGE_TRACE=1` pending broader exemption.)*
