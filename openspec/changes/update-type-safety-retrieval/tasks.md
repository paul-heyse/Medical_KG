# Implementation Tasks

## 1. Retrieval Core Typing

- [ ] 1.1 Define TypedDicts / Protocols for cache entries, ranking inputs, and fusion outputs in `retrieval/cache.py`, `fusion.py`, `neighbor.py`
- [ ] 1.2 Refactor `retrieval/service.py` to accept typed request DTOs and return typed `RetrievalResult` objects without casts
- [ ] 1.3 Enforce typed intent classification and ontology expander interfaces (async + sync) to eliminate `Any`

## 2. API & Optional Dependencies

- [ ] 2.1 Update FastAPI route dependencies and response models to use the new typed service interfaces (no unchecked dict serialization)
- [ ] 2.2 Extend optional dependency shims (httpx/redis/embedding clients) with typed facades required by retrieval

## 3. Tests & Verification

- [ ] 3.1 Update retrieval integration/unit tests to leverage typed fixtures and assert typed responses
- [ ] 3.2 Run `mypy --strict src/Medical_KG/retrieval src/Medical_KG/api/tests/retrieval` with zero errors
- [ ] 3.3 Execute retrieval API integration tests to confirm behavior (existing suites or new additions)
