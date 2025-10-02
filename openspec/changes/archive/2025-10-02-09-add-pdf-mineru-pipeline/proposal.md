# Add PDF MinerU Pipeline

## Why

PDF-based medical literature (guidelines, full-text articles not in PMC OA) requires OCR-quality parsing with table extraction, reading order, and layout preservation. MinerU provides GPU-accelerated parsing but MUST run as a separate, manual step (no automatic transition to chunking) to manage GPU resources and enable QA gates.

## What Changes

- Create MinerU runner service/script (GPU-only; Ubuntu 24.04)
- Implement two-phase PDF pipeline: download → (STOP) → mineru-run (GPU) → IR → (STOP) → postpdf-start
- Add GPU enforcement (REQUIRE_GPU=1; fail if nvidia-smi or CUDA unavailable; exit code 99)
- Implement ledger gates (pdf_downloaded → pdf_ir_ready states)
- Create MinerU post-processing (header/footer removal, hyphenation repair, caption linking, IMRaD labeling)
- Implement MinerU QA gates (reading order sanity ≥85%, header/footer removal verified, table rectangularization)
- Add commands: `med ingest pdf`, `med mineru-run`, `med postpdf-start`
- Store MinerU artifacts (markdown, blocks JSON, tables HTML) and provenance (run_id, version)

## Impact

- **Affected specs**: NEW `pdf-processing` capability
- **Affected code**: NEW `/mineru_runner/`, updates to `/ops/ledger/`, `/ops/cli/`
- **Dependencies**: NVIDIA driver, CUDA, Docker with `--gpus all`, MinerU container (ghcr.io/opendatalab/mineru)
- **Infrastructure**: GPU nodes/queue for MinerU; object store for artifacts; no CPU fallback allowed
- **Licensing**: MinerU open-source; respects input PDF licenses
