## Why

Knowledge Graph (KG) and embeddings modules lack sufficient test coverage. KG writer, schema validators, batch operations, FHIR mapping, and query builders are untested. Embeddings GPU validator, monitoring, Qwen/SPLADE services, and model lifecycle are untested. These modules handle data persistence and compute-intensive operations—failures here cause data loss or service outages.

## What Changes

- Add unit tests for `KnowledgeGraphWriter`: verify Cypher statement generation, node/relationship merging, property updates, and batch operations.
- Test `KGSchemaValidator`: verify constraint enforcement, index creation, and schema migration.
- Test `FHIRMapper`: verify FHIR resource → graph transformation, CodeableConcept handling, and reference resolution.
- Test embeddings GPU validator: verify GPU availability checks, CUDA diagnostics, memory allocation, and fallback to CPU.
- Test embeddings monitoring: verify latency tracking, throughput metrics, and error rate reporting.
- Test `QwenEmbedder` and `SpladeEncoder`: mock model loading, verify embedding generation, batch processing, and error handling.
- Achieve 100% coverage for `src/Medical_KG/kg/` and `src/Medical_KG/embeddings/`.

## Impact

- Affected specs: `testing` (MODIFIED: Subsystem Test Depth to include KG and embeddings coverage requirements)
- Affected code: `tests/kg/` (new directory), `tests/embeddings/test_embeddings.py` (expand), `src/Medical_KG/kg/`, `src/Medical_KG/embeddings/`, `tests/conftest.py`
- Risks: mocking GPU operations may miss hardware-specific issues; mitigation via GPU CI runner for smoke tests (separate proposal).
