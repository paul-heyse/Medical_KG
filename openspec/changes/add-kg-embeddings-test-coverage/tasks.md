# Implementation Tasks

## 1. Test Fixtures & Mocks

- [ ] 1.1 Create sample Neo4j response JSON for nodes, relationships, and query results
- [ ] 1.2 Create `FakeNeo4jDriver` with in-memory graph for integration tests
- [ ] 1.3 Create sample FHIR resources (Patient, Condition, MedicationStatement, Observation)
- [ ] 1.4 Mock `torch.cuda` for GPU availability checks
- [ ] 1.5 Mock model loading for Qwen and SPLADE (return dummy embeddings)

## 2. KG Writer Tests

- [ ] 2.1 Test node creation: verify MERGE with properties
- [ ] 2.2 Test relationship creation: verify start/end node matching and properties
- [ ] 2.3 Test batch operations: verify transaction handling and rollback on error
- [ ] 2.4 Test property updates: verify SET operations and null handling
- [ ] 2.5 Test Cypher statement generation: verify parameterization and escaping
- [ ] 2.6 Test constraint violations: verify error handling for duplicate keys

## 3. KG Schema Validator Tests

- [ ] 3.1 Test constraint creation: verify uniqueness and existence constraints
- [ ] 3.2 Test index creation: verify full-text and property indexes
- [ ] 3.3 Test schema migration: verify adding/removing constraints and indexes
- [ ] 3.4 Test schema validation: verify graph conforms to declared schema
- [ ] 3.5 Test schema introspection: verify listing existing constraints/indexes

## 4. FHIR Mapper Tests

- [ ] 4.1 Test Patient → graph: verify demographics, identifiers, and extensions
- [ ] 4.2 Test Condition → graph: verify diagnosis codes, severity, and clinical status
- [ ] 4.3 Test MedicationStatement → graph: verify drug codes, dosage, and timing
- [ ] 4.4 Test Observation → graph: verify lab values, units, and reference ranges
- [ ] 4.5 Test reference resolution: verify links between resources (Patient → Condition)
- [ ] 4.6 Test CodeableConcept handling: verify SNOMED/LOINC/RxNorm code extraction

## 5. KG Query Builder Tests

- [ ] 5.1 Test simple node query: `MATCH (n:Label) WHERE n.prop = $val RETURN n`
- [ ] 5.2 Test relationship traversal: `MATCH (a)-[r:REL]->(b) RETURN a, r, b`
- [ ] 5.3 Test aggregation queries: `MATCH (n:Study) RETURN count(n)`
- [ ] 5.4 Test parameterization: verify safe parameter binding
- [ ] 5.5 Test query composition: verify builder pattern for complex queries

## 6. Embeddings GPU Validator Tests

- [ ] 6.1 Test GPU availability check: mock `torch.cuda.is_available()`
- [ ] 6.2 Test CUDA diagnostics: mock `torch.cuda.device_count()`, `get_device_name()`
- [ ] 6.3 Test memory allocation: mock `torch.cuda.mem_get_info()`
- [ ] 6.4 Test fallback to CPU: verify service continues with CPU embeddings
- [ ] 6.5 Test error reporting: verify alerts when GPU is unavailable

## 7. Embeddings Monitoring Tests

- [ ] 7.1 Test latency tracking: verify histogram updates per request
- [ ] 7.2 Test throughput metrics: verify counter increments per batch
- [ ] 7.3 Test error rate: verify counter increments on exceptions
- [ ] 7.4 Test model info labels: verify model name, version, device in metrics

## 8. Qwen & SPLADE Tests

- [ ] 8.1 Test model loading: mock `transformers.AutoModel.from_pretrained()`
- [ ] 8.2 Test embedding generation: verify output shape and dtype
- [ ] 8.3 Test batch processing: verify batching logic and padding
- [ ] 8.4 Test error handling: verify graceful degradation on OOM or CUDA errors
- [ ] 8.5 Test normalization: verify L2 norm for Qwen embeddings
- [ ] 8.6 Test SPLADE sparsification: verify non-zero indices and values

## 9. Coverage & Validation

- [ ] 9.1 Run `pytest tests/kg/ tests/embeddings/ --cov=src/Medical_KG/kg --cov=src/Medical_KG/embeddings --cov-report=term-missing`
- [ ] 9.2 Verify 100% coverage for all KG and embeddings modules
- [ ] 9.3 Ensure no Neo4j or GPU calls in test suite (mock all external dependencies)
- [ ] 9.4 Document KG and embeddings test patterns in respective README files
