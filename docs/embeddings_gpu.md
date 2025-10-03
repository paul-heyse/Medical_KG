# GPU Embedding Service

## vLLM Deployment

- Model: `Qwen/Qwen3-Embedding-8B`
- Command: `python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen3-Embedding-8B --task embedding --dtype bfloat16 --tensor-parallel-size 1 --max-model-len 32768 --gpu-memory-utilization 0.92 --trust-remote-code`
- Endpoint: OpenAI-compatible `/v1/embeddings` on port 8000; health probe at `/health`.

Enable autoscaling with a GPU-aware HPA (metrics: GPU util, request queue depth). Configure readiness probes to hit `/health` with a two-second timeout.

## GPU Prerequisites

- NVIDIA driver ≥ 550 and CUDA toolkit matching container runtime.
- NVIDIA Container Toolkit on Ubuntu 24.04 (`nvidia-container-toolkit` package + `nvidia-ctk runtime configure`).
- Export `REQUIRE_GPU=1` in the runtime environment; the service fails fast with exit code 99 when CUDA is unavailable.

## Failure Runbook

1. **vLLM Unreachable** – `EmbeddingService` retries transient errors. If the health check fails, redeploy the pod and confirm network ACLs allow port 8000.
2. **GPU OOM** – reduce `QwenEmbeddingClient.batch_size` or SPLADE `batch_size`; monitor memory via `nvidia-smi` in the pod.
3. **GPU Missing** – run `enforce_gpu_or_exit()` during startup; investigate driver installation and `nvidia-smi` output if the process exits with code 99.
4. **SPLADE Model Download Issues** – ensure HuggingFace credentials (if required) are mounted; for offline deployments, pre-populate the cache volume.
