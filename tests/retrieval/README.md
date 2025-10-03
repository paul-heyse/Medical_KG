# Retrieval Test Suite

This directory contains unit and integration tests targeting the retrieval subsystem.

- `test_intent_classifier.py` validates the regex-driven intent classifier across entity lookups, pathway questions, and fallbacks.
- `test_service_orchestration.py` exercises the async `RetrievalService`, covering dense, sparse, and graph-like retrieval paths, hybrid fusion fallback, and deduplication semantics.
- `test_caching.py` covers the shared TTL cache helper as well as the query cache behaviour on the `RetrievalService` facade.
- `test_neighbor_merger.py` asserts neighbour coalescing logic when merging sequential chunks from the same document.
- `test_ontology_expander.py` checks deterministic ontology expansion and synonym lookups.
- `test_api_integration.py` drives the FastAPI `/retrieve` endpoint through the production router, checking success and authentication failure scenarios.

Fixtures for fake clients and canned payloads live in `tests/conftest.py` and are reused across the suite to keep orchestration deterministic and offline.
