# Implementation Tasks

## 1. GPU Infrastructure & Enforcement

- [x] 1.1 Implement GPU detection (nvidia-smi check; torch.cuda.is_available())
- [x] 1.2 Add REQUIRE_GPU=1 environment flag enforcement (fail-fast with exit code 99)
- [x] 1.3 Create deployment for MinerU with vllm and with the ability to run multiple workers in parallel
- [x] 1.4 Test GPU failure modes (GPU unavailable → immediate abort, no CPU fallback)

## 2. MinerU Runner Service

- [x] 2.1 Create MinerU runner script/service consuming ledger (status=pdf_downloaded)
- [x] 2.2 Implement MinerU invocation (--input /in/doc.pdf --output /out/doc_key --ocr auto --tables html)
- [x] 2.3 Parse MinerU outputs (markdown.json, blocks.json, tables.html, offset_map.json)
- [x] 2.4 Convert MinerU artifacts to IR (Document, Block, Table objects with provenance)
- [x] 2.5 Update ledger state (pdf_ir_ready) and store artifacts URIs

## 3. Medical Post-Processing

- [x] 3.1 Implement two-column detection and reflow
- [x] 3.2 Implement header/footer suppression (repeated line detection across ≥60% pages)
- [x] 3.3 Implement dictionary-guarded hyphenation repair
- [x] 3.4 Implement caption linking (figure proximity detection)
- [x] 3.5 Implement IMRaD section labeling heuristics
- [x] 3.6 Implement clinical table intent tagging (HR/OR/RR patterns, AE/Grade patterns)

## 4. QA Gates

- [x] 4.1 Implement reading order sanity check (≥85% ascending y-coords per page)
- [x] 4.2 Implement header/footer removal verification
- [x] 4.3 Implement table rectangularization check (keep HTML if parsing fails)
- [x] 4.4 Implement OCR coverage threshold
- [x] 4.5 Implement text delta check (raw_text vs text ≤5% difference)
- [x] 4.6 Mark ledger mineru_failed on gate failures

## 5. Post-PDF Pipeline Gate

- [x] 5.1 Implement postpdf-start command (triggers chunk → facet → embed → index for pdf_ir_ready docs)
- [x] 5.2 Ensure GPU availability for downstream steps (embeddings require vLLM/SPLADE on GPU)
- [x] 5.3 Add manual/queue trigger support (no automatic transition from MinerU to chunking)

## 6. Provenance & Artifacts

- [x] 6.1 Store mineru_run_id, mineru_version in Document.meta
- [x] 6.2 Store artifact URIs (markdown_uri, blocks_uri, tables_uri) in Document.meta.mineru_artifacts
- [x] 6.3 Create char_to_page_bbox_map for span provenance
- [x] 6.4 Persist all artifacts to object store with versioning

## 7. CLI & Orchestration

- [x] 7.1 Create `med ingest pdf --uri <URL> --doc-key <KEY>` (download only, no auto)
- [x] 7.2 Create `med mineru-run --from-ledger --filter status=pdf_downloaded --gpus all --fail-if-no-gpu`
- [x] 7.3 Create `med postpdf-start --from-ledger --filter status=pdf_ir_ready --steps ir->chunk->facet->embed->index --gpus all`
- [x] 7.4 Add batch processing support (multiple PDFs in one MinerU run)

## 8. Monitoring & Metrics

- [x] 8.1 Emit metrics: mineru_pages_sec, mineru_failures_total, mineru_qa_gate_failures{gate_type}
- [x] 8.2 Add logging for MinerU stderr/stdout
- [x] 8.3 Create dashboard for GPU utilization and MinerU throughput

## 9. Testing

- [x] 9.1 Unit tests for post-processors (header/footer, hyphenation, IMRaD labeling)
- [x] 9.2 Integration test with sample medical PDFs (guideline, article, label)
- [x] 9.3 Test GPU enforcement (mock GPU unavailable → verify exit code 99)
- [x] 9.4 Test ledger state transitions (pdf_downloaded → pdf_ir_ready → postpdf complete)

## 10. Documentation

- [x] 10.1 Document GPU prerequisites (NVIDIA driver, CUDA, Container Toolkit)
- [x] 10.2 Write runbook for MinerU failures (QA gate violations, OCR issues, GPU OOM)
- [x] 10.3 Document manual trigger workflow (download → inspect → approve → mineru-run → postpdf-start)
