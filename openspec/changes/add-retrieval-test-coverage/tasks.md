# Implementation Tasks

## 1. Test Fixtures & Mocks

- [x] 1.1 Create `FakeQwenEmbedder`, `FakeSpladeEncoder`, `FakeNeo4jClient`, `FakeOpenSearchClient` in `tests/conftest.py`
- [x] 1.2 Provide sample query/document embeddings (numpy arrays or lists)
- [x] 1.3 Create sample graph results (Neo4j response JSON), vector results (OpenSearch JSON)
- [x] 1.4 Add fixtures for `RetrieveRequest` and expected `RetrieveResponse` payloads

## 2. Intent Classification Tests

- [x] 2.1 Test entity lookup detection ("What is pembrolizumab?", "NCT12345")
- [x] 2.2 Test pathway query detection ("How does EGFR signaling work?")
- [x] 2.3 Test open-ended question detection ("What are the latest cancer treatments?")
- [x] 2.4 Test fallback when intent is ambiguous

## 3. Retrieval Orchestration Tests

- [x] 3.1 Test semantic retrieval: query embedding → vector search → top-k results
- [x] 3.2 Test sparse retrieval: SPLADE encoding → BM25 search → top-k results
- [x] 3.3 Test graph retrieval: entity extraction → Cypher query → subgraph results
- [x] 3.4 Test hybrid fusion: combine semantic + sparse + graph with RRF
- [x] 3.5 Test rank normalization and deduplication logic

## 4. Caching Tests

- [x] 4.1 Test cache hit: identical query returns cached results
- [x] 4.2 Test cache miss: new query triggers retrieval
- [x] 4.3 Test TTL expiration: old cache entries are evicted
- [x] 4.4 Test cache invalidation on document updates

## 5. Neighbor Expansion Tests

- [x] 5.1 Test 1-hop expansion: retrieve directly related entities
- [x] 5.2 Test 2-hop expansion: retrieve entities through intermediates
- [x] 5.3 Test relationship filtering: include only specific edge types
- [x] 5.4 Test entity resolution: merge duplicate entities by identifier

## 6. Ontology Augmentation Tests

- [x] 6.1 Test synonym expansion: "cancer" → ["neoplasm", "malignancy", "tumor"]
- [x] 6.2 Test hypernym expansion: "lung cancer" → ["lung cancer", "cancer", "disease"]
- [x] 6.3 Test ontology lookup caching
- [x] 6.4 Test fallback when ontology service is unavailable

## 7. Authentication & Authorization Tests

- [x] 7.1 Test JWT validation: valid token → authorized request
- [ ] 7.2 Test JWT validation: expired token → 401 Unauthorized
- [x] 7.3 Test API key handling: valid key → authorized request
- [x] 7.4 Test scope enforcement: restricted scope → filtered results
- [x] 7.5 Test missing credentials → 401 Unauthorized

## 8. API Integration Tests

- [x] 8.1 Test `/retrieve` endpoint with mock service: success case
- [x] 8.2 Test `/retrieve` endpoint: validation error on malformed request
- [ ] 8.3 Test streaming response for large result sets
- [x] 8.4 Test rate limiting headers (`X-RateLimit-*`)

## 9. Coverage & Validation

- [ ] 9.1 Run `pytest tests/retrieval/ --cov=src/Medical_KG/retrieval --cov-report=term-missing`
- [ ] 9.2 Verify ≥95% coverage for all retrieval modules
- [x] 9.3 Ensure no external service calls in test suite
- [x] 9.4 Document retrieval test patterns in `tests/retrieval/README.md`
