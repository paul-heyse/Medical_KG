# Implementation Tasks

## 1. vLLM Deployment (Qwen3-Embedding-8B)

- [ ] 1.1 Deploy vLLM with Qwen/Qwen3-Embedding-8B model (--task embedding --dtype bfloat16 --tensor-parallel-size 1 --max-model-len 32768 --gpu-memory-utilization 0.92 --trust-remote-code)
- [ ] 1.2 Expose OpenAI-compatible /v1/embeddings endpoint (default port 8000)
- [ ] 1.3 Test embedding API (curl with sample text; verify 4096-D output)
- [ ] 1.4 Add health check endpoint
- [ ] 1.5 Configure autoscaling (HPA on GPU utilization or request queue depth)

## 2. GPU Enforcement

- [x] 2.1 Implement bootstrap checks (nvidia-smi succeeds; reports ≥1 GPU)
- [x] 2.2 Add PyTorch CUDA check (torch.cuda.is_available() must be true)
- [x] 2.3 Add vLLM reachability check (GET /health; must return 200)
- [ ] 2.4 Fail-fast with exit code 99 and clear diagnostics if any check fails
- [x] 2.5 Enforce REQUIRE_GPU=1 environment variable

## 3. Qwen Embedding Client

- [ ] 3.1 Implement OpenAI-compatible client (POST /v1/embeddings with model, input[])
- [x] 3.2 Add batching (group chunks into batches of 256; adjust to VRAM)
- [ ] 3.3 Add retry logic (transient vLLM errors; max 3 retries with backoff)
- [x] 3.4 Emit metrics (embed_chunks_sec, embed_latency_ms, embed_batch_size)
- [x] 3.5 Store embeddings (chunk.embedding_qwen as float[4096])

## 4. SPLADE-v3 Doc Expansion

- [ ] 4.1 Load naver/splade-v3 model checkpoint (HuggingFace; ensure GPU via device='cuda')
- [ ] 4.2 Tokenize chunk text + facet_json + table_lines (concatenate with separators)
- [ ] 4.3 Run SPLADE doc-mode forward pass (produces term→weight map)
- [x] 4.4 Keep top-K=400 terms with min_weight≥0.05; L2-normalize weights
- [x] 4.5 Store splade_terms as map<string,float> on Chunk
- [ ] 4.6 Batch processing (adjust batch size to GPU memory; target ≥10k chunks/hr/GPU)

## 5. SPLADE Query Encoder

- [ ] 5.1 Implement query-time SPLADE expansion (user query → weighted terms)
- [ ] 5.2 Construct OpenSearch query with rank_feature clauses
- [ ] 5.3 Cache query expansions (60s TTL; key=hash(query_text))

## 6. Neo4j Integration

- [ ] 6.1 Upsert :Chunk nodes with embedding_qwen property
- [ ] 6.2 Create vector index chunk_qwen_idx (4096-D, cosine similarity)
- [ ] 6.3 Test KNN query (CALL db.index.vector.queryNodes('chunk_qwen_idx', k, queryEmbedding))

## 7. OpenSearch Integration

- [ ] 7.1 Index splade_terms as rank_features field type
- [ ] 7.2 Test rank_feature query (match clauses + rank_feature boost)
- [ ] 7.3 Verify BM25 + SPLADE hybrid scoring

## 8. Throughput & Performance

- [ ] 8.1 Benchmark Qwen embedding (target ≥1,000 chunks/min/GPU; tune batch size)
- [ ] 8.2 Benchmark SPLADE expansion (target ≥10k chunks/hr/GPU)
- [ ] 8.3 Monitor GPU utilization (aim for 80-90% under load)
- [ ] 8.4 Profile memory usage (adjust batch sizes if OOM)

## 9. Failure Modes & Monitoring

- [ ] 9.1 Handle vLLM unavailable (fail job; do not fall back to CPU)
- [ ] 9.2 Handle GPU OOM (reduce batch size; retry)
- [ ] 9.3 Emit alerts (vLLM down; GPU not visible; throughput below threshold)
- [ ] 9.4 Create Grafana dashboard (GPU utilization, vLLM latency, SPLADE throughput)

## 10. Testing

- [x] 10.1 Unit tests (mock vLLM API; verify batching and retries)
- [x] 10.2 Integration tests (embed sample chunks; verify 4096-D vectors; verify SPLADE terms)
- [x] 10.3 Test GPU enforcement (mock GPU unavailable → verify exit code 99)
- [ ] 10.4 Load test (embed 10k chunks; measure throughput and latency)

## 11. Documentation

- [ ] 11.1 Document vLLM deployment (model, hardware requirements, startup command)
- [ ] 11.2 Document GPU prerequisites (NVIDIA driver, CUDA, Container Toolkit on Ubuntu 24.04)
- [ ] 11.3 Write runbook for common failures (vLLM OOM, GPU not visible, SPLADE model download issues)
