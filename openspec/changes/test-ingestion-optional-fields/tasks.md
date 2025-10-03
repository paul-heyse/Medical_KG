# Implementation Tasks

## 1. Fixture Creation for Optional Field Variants

- [x] 1.1 Create terminology fixtures with all optional fields present (6 adapters)
- [x] 1.2 Create terminology fixtures with all optional fields absent (6 adapters)
- [x] 1.3 Create clinical fixtures with optional field variants (3 adapters, high complexity)
- [ ] 1.4 Create literature fixtures with optional field variants (3 adapters)
- [ ] 1.5 Create guidelines fixtures with optional field variants (2 adapters)
- [ ] 1.6 Create knowledge base fixtures with optional field variants (4 adapters)

## 2. Parametrized Test Implementation

- [x] 2.1 Create parametrized test in test_adapters.py for terminology adapters (18 cases)
- [x] 2.2 Create parametrized test for clinical adapters (24 cases, focus on ClinicalTrials)
- [x] 2.3 Create parametrized test for literature adapters (12 cases)
- [ ] 2.4 Create parametrized test for guidelines adapters (6 cases)
- [ ] 2.5 Create parametrized test for knowledge base adapters (8 cases)

## 3. Dedicated Optional Fields Test Module

- [x] 3.1 Create `tests/ingestion/test_optional_fields.py` module
- [x] 3.2 Implement test verifying Document.content stable regardless of optional field presence
- [x] 3.3 Implement test verifying Document.metadata doesn't include keys for absent optional fields
- [x] 3.4 Implement test verifying validation doesn't fail on absent optional fields
- [x] 3.5 Document test patterns for future adapter additions

## 4. Documentation & Analysis

- [ ] 4.1 Document which optional fields are "commonly present" in module docstrings (based on test fixtures)
- [ ] 4.2 Add inline comments in adapters explaining optional field handling
- [ ] 4.3 Update test README explaining optional field testing strategy
- [ ] 4.4 Generate coverage report showing NotRequired field coverage
- [ ] 4.5 Verify every NotRequired field appears in ≥2 test scenarios (present + absent)
