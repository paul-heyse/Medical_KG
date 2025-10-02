# Embeddings Capability

## ADDED Requirements

### Requirement: vLLM Dense Embedding Service

The system SHALL serve Qwen3-Embedding-8B model via vLLM with GPU-only enforcement producing 4096-dimensional embeddings.

#### Scenario: vLLM server initialization

- **WHEN** starting embedding service
- **THEN** the system SHALL load Qwen3-Embedding-8B model on GPU via vLLM with --enforce-eager compilation and --trust-remote-code

#### Scenario: Embedding request

- **WHEN** POST /v1/embeddings with {texts[], model: "Qwen3-Embedding-8B"}
- **THEN** the system SHALL return embeddings[] as 4096-D float32 vectors normalized to unit length

#### Scenario: Batch processing

- **WHEN** embedding batch of chunks
- **THEN** the system SHALL process up to batch_size=64 texts in parallel and achieve throughput ≥2.5K tokens/s/GPU

### Requirement: SPLADE Sparse Expansion

The system SHALL provide SPLADE-v3 model for doc-side term expansion with GPU-only enforcement.

#### Scenario: SPLADE model loading

- **WHEN** initializing SPLADE service
- **THEN** the system SHALL load naver/splade-v3 or equivalent from HuggingFace with GPU placement

#### Scenario: Term expansion

- **WHEN** given text input
- **THEN** the system SHALL compute SPLADE vector and extract top-K=50 terms with weights >0.5 as {term: weight} map

#### Scenario: Vocabulary handling

- **WHEN** SPLADE produces term not in BERT vocab
- **THEN** the system SHALL apply WordPiece tokenization and aggregate subword weights

### Requirement: GPU Enforcement

The system SHALL enforce GPU availability for all embedding operations and SHALL NOT fall back to CPU.

#### Scenario: GPU detection

- **WHEN** service initializes
- **THEN** the system SHALL verify torch.cuda.is_available() and nvidia-smi reports ≥1 GPU with compute capability ≥7.0

#### Scenario: GPU unavailable failure

- **WHEN** GPU detection fails
- **THEN** the system SHALL exit with code 99 and log "GPU required for embeddings but not available"

#### Scenario: CPU fallback rejection

- **WHEN** CUDA_VISIBLE_DEVICES="" or GPU memory exhausted
- **THEN** the system SHALL NOT attempt CPU inference and SHALL fail fast with clear error message

### Requirement: Chunk Embedding Pipeline

The system SHALL compute and store embeddings for all chunks enabling dense retrieval.

#### Scenario: Embed chunks from ledger

- **WHEN** running `med embed --filter type=chunk status=chunked --modality dense`
- **THEN** the system SHALL fetch chunks, embed text via Qwen, and write embeddings to Neo4j and OpenSearch

#### Scenario: Dense vector storage in Neo4j

- **WHEN** chunk embedding completes
- **THEN** the system SHALL SET Chunk.embedding_qwen as float32[] and update vector index chunk_qwen_idx

#### Scenario: Dense vector storage in OpenSearch

- **WHEN** indexing chunk
- **THEN** the system SHALL include chunk_embedding_qwen field (dense_vector 4096 dims) for hybrid retrieval

### Requirement: Facet Embedding Pipeline

The system SHALL compute embeddings for facet summaries enabling intent-specific dense retrieval.

#### Scenario: Embed facets

- **WHEN** running `med embed --filter type=facet`
- **THEN** the system SHALL embed facet JSON strings (minified) and store as Chunk.facet_embedding_qwen

#### Scenario: Separate facet index

- **WHEN** facet embeddings enabled
- **THEN** the system SHALL create optional OpenSearch index facets_v1 with facet_embedding_qwen field

#### Scenario: Skip facet embedding by default

- **WHEN** EMBED_FACETS=false (default)
- **THEN** the system SHALL compute chunk text embeddings only (facet embeddings optional to save space)

### Requirement: Concept Embedding Pipeline

The system SHALL compute embeddings for catalog concepts enabling candidate generation via KNN.

#### Scenario: Embed concepts

- **WHEN** running `med catalog refresh`
- **THEN** the system SHALL embed label + definition + top-3 synonyms for each concept and store as Concept.embedding_qwen

#### Scenario: Concept vector index

- **WHEN** concept embeddings computed
- **THEN** the system SHALL CREATE VECTOR INDEX concept_qwen_idx FOR (c:Concept) ON c.embedding_qwen WITH OPTIONS {indexProvider: "lucene", dimensions: 4096, similarityFunction: "cosine"}

#### Scenario: Incremental concept embedding

- **WHEN** new concepts added to catalog
- **THEN** the system SHALL compute embeddings for new concepts only without recomputing existing

### Requirement: SPLADE Expansion Pipeline

The system SHALL compute SPLADE expansions for chunks and concepts enabling sparse retrieval.

#### Scenario: Chunk SPLADE expansion

- **WHEN** running `med embed --modality splade`
- **THEN** the system SHALL compute SPLADE vectors for chunks and store top-50 terms as Chunk.splade_terms[]

#### Scenario: SPLADE terms in OpenSearch

- **WHEN** indexing chunk with SPLADE
- **THEN** the system SHALL copy splade_terms to OpenSearch chunks_v1 index with BM25F field boost

#### Scenario: Concept SPLADE expansion

- **WHEN** catalog refresh runs
- **THEN** the system SHALL compute SPLADE for concepts and store as Concept.splade_terms[] in OpenSearch concepts_v1 index

### Requirement: Batch Processing and Throughput

The system SHALL optimize batch sizes and parallelism to achieve target throughput on GPU.

#### Scenario: Dynamic batch sizing

- **WHEN** GPU memory allows
- **THEN** the system SHALL auto-tune batch_size up to 128 for short texts (<200 tokens) or down to 32 for long texts (>500 tokens)

#### Scenario: Throughput measurement

- **WHEN** embedding batches
- **THEN** the system SHALL emit metrics embed_tokens_per_second_gpu, embed_requests_total, embed_duration_seconds

#### Scenario: Target throughput

- **WHEN** processing on single A100 GPU
- **THEN** the system SHALL achieve ≥2.5K tokens/s for Qwen embeddings and ≥3K tokens/s for SPLADE

### Requirement: Error Handling

The system SHALL handle embedding failures gracefully and retry transient errors.

#### Scenario: GPU OOM

- **WHEN** batch causes CUDA out-of-memory error
- **THEN** the system SHALL reduce batch_size by 50%, retry, and log GPU memory stats

#### Scenario: vLLM service unavailable

- **WHEN** embedding request to vLLM fails with connection error
- **THEN** the system SHALL retry with exponential backoff (max 3 retries) and fail batch if still unavailable

#### Scenario: Invalid text

- **WHEN** chunk text is empty or exceeds max_length (8192 tokens for Qwen)
- **THEN** the system SHALL skip embedding, log warning, and set Chunk.embedding_qwen=null

### Requirement: API Endpoints

The system SHALL provide API endpoints for on-demand embedding computation.

#### Scenario: Embed text endpoint

- **WHEN** POST /embed with {texts[], model: "qwen"|"splade"}
- **THEN** the system SHALL return embeddings[] or splade_terms[] respectively

#### Scenario: Batch embed chunks

- **WHEN** POST /embed/chunks with {chunk_ids[], modality: dense|sparse|both}
- **THEN** the system SHALL embed all specified chunks and return {embedded_count, failed[]}

#### Scenario: Re-embed after model update

- **WHEN** POST /embed/recompute with {object_type: chunk|concept, filter}
- **THEN** the system SHALL recompute embeddings for matching objects using current model version

### Requirement: Model Versioning

The system SHALL track embedding model versions and enable migration when models are updated.

#### Scenario: Model version metadata

- **WHEN** computing embedding
- **THEN** the system SHALL store model_name, model_version, embedding_dim in object metadata

#### Scenario: Version detection

- **WHEN** querying embeddings
- **THEN** the system SHALL verify model_version matches current version and warn if mismatch detected

#### Scenario: Migration support

- **WHEN** embedding model is upgraded
- **THEN** the system SHALL provide migration command to recompute all embeddings with new model

### Requirement: Monitoring and Metrics

The system SHALL emit comprehensive metrics for embedding services.

#### Scenario: Service health

- **WHEN** monitoring embedding services
- **THEN** the system SHALL expose /health endpoint reporting GPU availability, model loaded, throughput

#### Scenario: Throughput metrics

- **WHEN** embeddings are computed
- **THEN** the system SHALL emit embed_tokens_per_second{model, gpu_type}, embed_batch_size_current

#### Scenario: GPU utilization

- **WHEN** embedding service is running
- **THEN** the system SHALL emit gpu_utilization_percent{model, device}, gpu_memory_used_bytes{model, device}
