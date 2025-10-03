# Implementation Tasks

## 1. Test Fixtures & Mocks

- [ ] 1.1 Create `FakeQwenEmbedder`, `FakeSpladeEncoder`, `FakeNeo4jClient`, `FakeOpenSearchClient` in `tests/conftest.py`
- [ ] 1.2 Provide sample query/document embeddings (numpy arrays or lists)
- [ ] 1.3 Create sample graph results (Neo4j response JSON), vector results (OpenSearch JSON)
- [ ] 1.4 Add fixtures for `RetrieveRequest` and expected `RetrieveResponse` payloads

## 2. Intent Classification Tests

- [ ] 2.1 Test entity lookup detection ("What is pembrolizumab?", "NCT12345")
- [ ] 2.2 Test pathway query detection ("How does EGFR signaling work?")
- [ ] 2.3 Test open-ended question detection ("What are the latest cancer treatments?")
- [ ] 2.4 Test fallback when intent is ambiguous

## 3. Retrieval Orchestration Tests

- [ ] 3.1 Test semantic retrieval: query embedding → vector search → top-k results
- [ ] 3.2 Test sparse retrieval: SPLADE encoding → BM25 search → top-k results
- [ ] 3.3 Test graph retrieval: entity extraction → Cypher query → subgraph results
- [ ] 3.4 Test hybrid fusion: combine semantic + sparse + graph with RRF
- [ ] 3.5 Test rank normalization and deduplication logic

## 4. Caching Tests

- [ ] 4.1 Test cache hit: identical query returns cached results
- [ ] 4.2 Test cache miss: new query triggers retrieval
- [ ] 4.3 Test TTL expiration: old cache entries are evicted
- [ ] 4.4 Test cache invalidation on document updates

## 5. Neighbor Expansion Tests

- [ ] 5.1 Test 1-hop expansion: retrieve directly related entities
- [ ] 5.2 Test 2-hop expansion: retrieve entities through intermediates
- [ ] 5.3 Test relationship filtering: include only specific edge types
- [ ] 5.4 Test entity resolution: merge duplicate entities by identifier

## 6. Ontology Augmentation Tests

- [ ] 6.1 Test synonym expansion: "cancer" → ["neoplasm", "malignancy", "tumor"]
- [ ] 6.2 Test hypernym expansion: "lung cancer" → ["lung cancer", "cancer", "disease"]
- [ ] 6.3 Test ontology lookup caching
- [ ] 6.4 Test fallback when ontology service is unavailable

## 7. Authentication & Authorization Tests

- [ ] 7.1 Test JWT validation: valid token → authorized request
- [ ] 7.2 Test JWT validation: expired token → 401 Unauthorized
- [ ] 7.3 Test API key handling: valid key → authorized request
- [ ] 7.4 Test scope enforcement: restricted scope → filtered results
- [ ] 7.5 Test missing credentials → 401 Unauthorized

## 8. API Integration Tests

- [ ] 8.1 Test `/retrieve` endpoint with mock service: success case
- [ ] 8.2 Test `/retrieve` endpoint: validation error on malformed request
- [ ] 8.3 Test streaming response for large result sets
- [ ] 8.4 Test rate limiting headers (`X-RateLimit-*`)

## 9. Coverage & Validation

- [ ] 9.1 Run `pytest tests/retrieval/ --cov=src/Medical_KG/retrieval --cov-report=term-missing`
- [ ] 9.2 Verify 100% coverage for all retrieval modules
- [ ] 9.3 Ensure no external service calls in test suite
- [ ] 9.4 Document retrieval test patterns in `tests/retrieval/README.md`
