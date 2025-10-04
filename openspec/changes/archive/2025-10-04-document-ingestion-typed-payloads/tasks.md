# Implementation Tasks

## 1. Create Typed Contracts Guide

- [ ] 1.1 Create `docs/ingestion_typed_contracts.md` with outline structure
- [ ] 1.2 Write "TypedDict Basics" section explaining mixin patterns
- [ ] 1.3 Write "NotRequired Fields" section with conventions and examples
- [ ] 1.4 Write "Type Guards" section explaining when and how to use them
- [ ] 1.5 Add complete terminology adapter example (MeSH or UMLS)
- [ ] 1.6 Add complete literature adapter example (PubMed)
- [ ] 1.7 Add complete clinical adapter example (ClinicalTrials)
- [ ] 1.8 Add troubleshooting section for common mypy errors

## 2. Update Ingestion Runbooks

- [ ] 2.1 Add "Adding a New Typed Adapter" section to ingestion_runbooks.md
- [ ] 2.2 Create step-by-step scaffolding guide with code templates
- [ ] 2.3 Write migration guide for converting existing Any-typed adapters
- [ ] 2.4 Add section on testing typed adapters
- [ ] 2.5 Document payload family selection criteria

## 3. Update Contributing Guidelines

- [ ] 3.1 Add "Typed Adapter Requirements" section to CONTRIBUTING.md
- [ ] 3.2 Create mypy strict compliance checklist
- [ ] 3.3 Add code review checklist for adapter PRs
- [ ] 3.4 Mandate TypedDict definitions for new adapters
- [ ] 3.5 Document CI checks that enforce typing

## 4. Module Docstring Enhancement

- [ ] 4.1 Add comprehensive module docstring to ingestion/types.py
- [ ] 4.2 Document each payload family union (when to use, what adapters use it)
- [ ] 4.3 Document mixin TypedDicts with inheritance examples
- [ ] 4.4 Add docstrings to type guard functions explaining their purpose
- [ ] 4.5 Include cross-references to docs/ingestion_typed_contracts.md

## 5. Review & Validation

- [ ] 5.1 Have 2 developers review documentation for clarity
- [ ] 5.2 Test documentation by having contributor create sample adapter following guide
- [ ] 5.3 Ensure all code examples are valid and tested
- [ ] 5.4 Link documentation from README and relevant module docstrings
- [ ] 5.5 Add documentation to PR template checklist
