# Implementation Tasks

## 1. Model Layer
- [ ] 1.1 Convert extraction models to typed BaseModel declarations (explicit field annotations, validators).
- [ ] 1.2 Define typed protocols/aliases for span, evidence, and facet cross-links used by extraction outputs.
- [ ] 1.3 Update normalizers and parsers to return typed structures without `Any` leakage.

## 2. Service & Metrics
- [ ] 2.1 Add type annotations to extraction service entrypoints and helper functions.
- [ ] 2.2 Refine metrics calculations to operate on `Sequence`/`Mapping` instead of dynamic attributes.
- [ ] 2.3 Ensure KG writer utilities accept typed extraction payloads with validation layers.

## 3. Testing & Validation
- [ ] 3.1 Expand unit tests to cover typed models and ensure backwards-compatible serialization.
- [ ] 3.2 Run `mypy --strict src/Medical_KG/extraction` and fix all remaining errors.
- [ ] 3.3 Execute targeted pytest suite covering extraction services.
