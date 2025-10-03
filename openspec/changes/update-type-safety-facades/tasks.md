# Implementation Tasks

## 1. Optional Dependency Facades

- [ ] 1.1 Define Protocols for tensor/embedding clients (torch, tiktoken) and provide typed fallbacks
- [ ] 1.2 Type locust and httpx client utilities used in tests and load scripts
- [ ] 1.3 Ensure prometheus metrics exports use typed stubs when dependency absent

## 2. Test Fixture Typing

- [ ] 2.1 Annotate pytest fixtures in `tests/cli`, `tests/ingestion`, `tests/retrieval`
- [ ] 2.2 Update async helper utilities to expose typed Protocol-based mocks
- [ ] 2.3 Remove remaining `Any` casts in conftest

## 3. Documentation & Enforcement

- [ ] 3.1 Expand `docs/type_safety.md` with optional dependency examples
- [ ] 3.2 Update CONTRIBUTING to reference new fixture models
- [ ] 3.3 Validate `mypy --strict tests` passes for directories covered
