## Why

Retrieval service tests are missing entirely. The service orchestrates semantic + sparse + graph retrieval, hybrid fusion, intent classification, caching, and neighbor expansion. Auth middleware, ranking fallbacks, and ontology-augmented retrieval are untested. This creates a blind spot for one of the system's most critical components.

## What Changes

- Add unit tests for `RetrievalService`: mock `QwenEmbedder`, `SpladeEncoder`, `Neo4jClient`, `OpenSearchClient` and verify orchestration logic.
- Test intent classification: recognize entity lookups, pathway queries, and open-ended questions.
- Test fusion logic: verify RRF scoring, rank normalization, and deduplication.
- Test caching: verify cache hits/misses, TTL expiration, and invalidation.
- Test neighbor expansion: verify graph traversal depth, relationship filtering, and entity resolution.
- Test ontology augmentation: verify query expansion with synonyms and hypernyms.
- Test API authentication and authorization: verify JWT validation, API key handling, and scope enforcement.
- Achieve 100% coverage for `src/Medical_KG/retrieval/`.

## Impact

- Affected specs: `testing` (MODIFIED: Subsystem Test Depth to include retrieval coverage requirements)
- Affected code: `tests/retrieval/` (new directory), `src/Medical_KG/retrieval/`, `tests/conftest.py` (new fixtures)
- Risks: mocking graph/vector stores may miss performance issues; mitigation via load testing (separate proposal).
