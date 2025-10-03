# Add Embeddings (GPU-Only: SPLADE-v3 + Qwen3 via vLLM)

## Why

Hybrid retrieval (sparse + dense) dramatically outperforms BM25-only or dense-only for medical domain. SPLADE-v3 provides learned sparse expansions; Qwen3-Embedding-8B provides 4096-D dense vectors. Both require GPU (vLLM for Qwen; PyTorch CUDA for SPLADE). No CPU fallback ensures consistent, production-grade performance.

## What Changes

- Deploy vLLM serving Qwen3-Embedding-8B (OpenAI-compatible /v1/embeddings endpoint) on GPU (Ubuntu 24.04)
- Implement SPLADE-v3 doc-side expansion (GPU via PyTorch; top-K=400 terms, min_weight≥0.05, L2-normalize)
- Add GPU enforcement (REQUIRE_GPU=1; nvidia-smi check; torch.cuda.is_available(); fail-fast exit code 99)
- Create embedding service (batch API; 256 chunks/batch for Qwen; adjust to VRAM)
- Implement SPLADE query-encoder (on-the-fly at retrieval time)
- Store embeddings: chunk.embedding_qwen (4096-D float[]), chunk.splade_terms (map<string,float>)
- Persist to Neo4j (:Chunk.embedding_qwen) and OpenSearch (splade_terms as rank_features)
- Add throughput targets (≥1,000 chunks/min/GPU for Qwen; ≥10k chunks/hr/GPU for SPLADE)

## Impact

- **Affected specs**: NEW `embeddings-gpu` capability
- **Affected code**: NEW `/embeddings/qwen_vllm_client/`, `/embeddings/splade_v3_expander/`
- **Dependencies**: NVIDIA driver, CUDA, vLLM, naver/splade-v3 checkpoint, PyTorch with CUDA
- **Infrastructure**: GPU nodes (at least 1x A100/H100 or 2x A10G for production); vLLM service endpoint
- **Downstream**: Retrieval (dense KNN + SPLADE scoring); Neo4j vector index; OpenSearch rank_features
