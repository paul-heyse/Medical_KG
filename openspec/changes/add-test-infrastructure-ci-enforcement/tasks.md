# Implementation Tasks

## 1. Shared Fixtures

- [ ] 1.1 Create `document_factory` fixture: generate sample `Document` objects with configurable metadata
- [ ] 1.2 Create `chunk_factory` fixture: generate sample `Chunk` objects with text, embeddings, metadata
- [ ] 1.3 Create `facet_factory` fixture: generate sample facets (PICO, effect, AE, dose, eligibility)
- [ ] 1.4 Create `extraction_factory` fixture: generate sample extractions with evidence spans
- [ ] 1.5 Create `user_factory` fixture: generate sample users with roles and permissions
- [ ] 1.6 Create `api_response_factory` fixture: generate sample API responses for testing endpoints
- [ ] 1.7 Create `sample_pdf_bytes` fixture: provide small test PDF files as bytes

## 2. Async Test Helpers

- [ ] 2.1 Implement `AsyncMockTransport` for `httpx.AsyncClient` testing
- [ ] 2.2 Implement `async_test_client` fixture: wrap FastAPI app with `httpx.AsyncClient`
- [ ] 2.3 Implement `mock_async_iterator`: helper for mocking async generators
- [ ] 2.4 Implement `async_timeout_context`: helper for testing timeout behavior
- [ ] 2.5 Document async test patterns in `tests/README.md`

## 3. Fake Service Implementations

- [ ] 3.1 Implement `FakeNeo4jService`: in-memory graph with Cypher query support
- [ ] 3.2 Implement `FakeOpenSearchService`: in-memory index with search/filter support
- [ ] 3.3 Implement `FakeKafkaProducer`: record messages for verification
- [ ] 3.4 Implement `FakeLLMService`: return canned responses based on prompts
- [ ] 3.5 Implement `FakeEmbeddingService`: return deterministic embeddings
- [ ] 3.6 Document fake service usage in `tests/README.md`

## 4. Pytest Configuration

- [ ] 4.1 Set `pytest.ini` or `pyproject.toml` coverage minimum to 95%
- [ ] 4.2 Configure per-file coverage budgets for complex modules
- [ ] 4.3 Enable `--cov-fail-under=95` in CI
- [ ] 4.4 Configure coverage exclusions for `__pycache__`, `tests/`, `ops/`
- [ ] 4.5 Enable `pytest-xdist` for parallel test execution

## 5. CI Coverage Integration

- [ ] 5.1 Update `.github/workflows/test.yml`: add coverage step with `pytest --cov`
- [ ] 5.2 Generate HTML coverage report: `pytest --cov --cov-report=html`
- [ ] 5.3 Generate XML coverage report: `pytest --cov --cov-report=xml`
- [ ] 5.4 Upload coverage reports as artifacts: use `actions/upload-artifact`
- [ ] 5.5 Comment coverage summary on PRs: use `coverage-comment-action` or similar
- [ ] 5.6 Fail CI if coverage drops below 95%: use `--cov-fail-under=95`

## 6. Coverage Badge & Dashboard

- [ ] 6.1 Integrate with shields.io: generate coverage badge from CI
- [ ] 6.2 Or integrate with Codecov: upload reports, enable dashboard
- [ ] 6.3 Add badge to `README.md`: display current coverage percentage
- [ ] 6.4 Configure coverage tracking: enable historical coverage trends

## 7. Test Documentation

- [ ] 7.1 Create `tests/README.md`: overview of test structure and philosophy
- [ ] 7.2 Document fixture usage: provide examples for each major fixture
- [ ] 7.3 Document mocking patterns: examples for `httpx`, `Neo4j`, `OpenSearch`, LLMs
- [ ] 7.4 Document async testing: examples for `AsyncClient`, `mock_async_iterator`
- [ ] 7.5 Document contribution guidelines: how to add tests for new modules
- [ ] 7.6 Document coverage maintenance: how to update budgets, handle exceptions

## 8. Migration & Validation

- [ ] 8.1 Migrate existing tests to use new fixtures (incremental, by module)
- [ ] 8.2 Verify all tests pass with new infrastructure: `pytest -v`
- [ ] 8.3 Verify coverage meets 95% threshold: `pytest --cov --cov-report=term-missing`
- [ ] 8.4 Verify CI pipeline passes: push changes, check GitHub Actions
- [ ] 8.5 Verify coverage reports are published: check artifacts and PR comments
