# PDF Processing Capability

## ADDED Requirements

### Requirement: GPU Enforcement

The system SHALL enforce GPU availability for all PDF processing operations and SHALL NOT fall back to CPU processing.

#### Scenario: GPU available

- **WHEN** nvidia-smi reports available GPUs and torch.cuda.is_available() returns true
- **THEN** the system SHALL proceed with MinerU processing

#### Scenario: GPU unavailable

- **WHEN** GPU detection fails or no CUDA devices are present
- **THEN** the system SHALL exit with code 99 and log "GPU required for PDF processing but not available"

#### Scenario: REQUIRE_GPU flag enforcement

- **WHEN** REQUIRE_GPU=1 environment variable is set and GPU is unavailable
- **THEN** the system SHALL fail immediately without processing any documents

### Requirement: MinerU Runner Service

The system SHALL provide a MinerU runner service that consumes ledger entries with status=pdf_downloaded and produces medical-grade intermediate representations.

#### Scenario: Process PDF from ledger

- **WHEN** ledger contains entry with status=pdf_downloaded and valid PDF URI
- **THEN** the runner SHALL invoke MinerU with flags --ocr auto --tables html and write output to IR format

#### Scenario: Parallel worker execution

- **WHEN** multiple PDFs are queued
- **THEN** the system SHALL support configurable parallel workers (default 4) each with dedicated GPU allocation

#### Scenario: State transitions

- **WHEN** MinerU processing starts
- **THEN** ledger state SHALL transition pdf_downloaded → mineru_inflight → pdf_ir_ready (on success) or mineru_failed (on error)

### Requirement: Medical Post-Processing

The system SHALL apply medical-specific post-processing to MinerU outputs including two-column detection, header/footer suppression, and reference normalization.

#### Scenario: Two-column detection

- **WHEN** processing a medical journal article with two-column layout
- **THEN** the system SHALL detect column boundaries via x-coordinate clustering and reflow text in reading order

#### Scenario: Header/footer suppression

- **WHEN** analyzing page-level text blocks
- **THEN** the system SHALL identify repeated lines appearing on ≥60% of pages and mark them as headers/footers for exclusion

#### Scenario: IMRaD section labeling

- **WHEN** processing medical articles
- **THEN** the system SHALL detect IMRaD sections (Introduction, Methods, Results, Discussion) via heading patterns and label blocks accordingly

### Requirement: Quality Assurance Gates

The system SHALL enforce QA gates on MinerU output and SHALL reject documents that fail quality thresholds.

#### Scenario: Reading order validation

- **WHEN** analyzing block y-coordinates within each page
- **THEN** the system SHALL verify ≥85% of blocks have ascending y-coords and fail processing if threshold not met

#### Scenario: OCR quality check

- **WHEN** OCR was required for processing
- **THEN** the system SHALL verify mean confidence ≥0.80 per page and log warning if below threshold

#### Scenario: Table extraction verification

- **WHEN** processing documents with tables
- **THEN** the system SHALL verify HTML table structure is well-formed and contains ≥1 row with ≥2 cells

### Requirement: Post-PDF Pipeline Gate

The system SHALL provide a manual gate between MinerU completion and downstream processing (chunking, embedding, indexing).

#### Scenario: Automatic stop after MinerU

- **WHEN** MinerU completes successfully and ledger state becomes pdf_ir_ready
- **THEN** the system SHALL STOP and NOT automatically trigger chunking or embedding

#### Scenario: Manual postpdf-start command

- **WHEN** operator runs `med postpdf-start --filter status=pdf_ir_ready`
- **THEN** the system SHALL transition documents to auto_inflight and begin chunk → embed → index → extract pipeline

#### Scenario: GPU requirement for downstream

- **WHEN** postpdf-start is invoked
- **THEN** the system SHALL verify GPU availability for embedding services before proceeding

### Requirement: Provenance and Artifacts

The system SHALL store MinerU provenance metadata and artifact URIs for auditing and debugging.

#### Scenario: Store run metadata

- **WHEN** MinerU processing completes
- **THEN** Document.meta SHALL include mineru_run_id, mineru_version, mineru_cli_args, and processing_timestamp

#### Scenario: Artifact storage

- **WHEN** MinerU produces outputs (markdown, blocks JSON, tables HTML)
- **THEN** the system SHALL upload artifacts to object store and record URIs in Document.meta.mineru_artifacts

#### Scenario: QA metrics storage

- **WHEN** QA gates execute
- **THEN** the system SHALL store qa_metrics including reading_order_score, ocr_confidence_mean, table_count, header_footer_suppressed_count

### Requirement: Error Handling and Recovery

The system SHALL handle MinerU failures gracefully and provide clear diagnostics for recovery.

#### Scenario: MinerU process crash

- **WHEN** MinerU subprocess exits with non-zero code
- **THEN** the system SHALL capture stderr, log failure reason, set ledger state to mineru_failed, and continue with next document

#### Scenario: GPU OOM error

- **WHEN** MinerU fails with CUDA out-of-memory error
- **THEN** the system SHALL log GPU memory stats, mark document for retry with smaller batch size, and continue

#### Scenario: Retry logic

- **WHEN** transient failure occurs (GPU OOM, timeout)
- **THEN** the system SHALL retry up to 3 times with exponential backoff (30s, 120s, 300s)

### Requirement: CLI Commands

The system SHALL provide CLI commands for PDF ingestion and MinerU batch processing.

#### Scenario: Ingest PDF only

- **WHEN** running `med ingest pdf --uri https://example.com/paper.pdf --doc-key DOC123`
- **THEN** the system SHALL download PDF, store in object store, set ledger state=pdf_downloaded, and exit without auto-processing

#### Scenario: Batch MinerU processing

- **WHEN** running `med mineru-run --from-ledger --filter status=pdf_downloaded --gpus all --fail-if-no-gpu`
- **THEN** the system SHALL process all matching documents in parallel across available GPUs

#### Scenario: Force reprocess

- **WHEN** running `med mineru-run --doc-key DOC123 --force`
- **THEN** the system SHALL reprocess document even if already in pdf_ir_ready state

### Requirement: Monitoring and Metrics

The system SHALL emit metrics for MinerU throughput, quality, and failures.

#### Scenario: Throughput metrics

- **WHEN** processing documents
- **THEN** the system SHALL emit mineru_pages_per_second, mineru_docs_processed_total, mineru_processing_duration_seconds

#### Scenario: Quality metrics

- **WHEN** QA gates execute
- **THEN** the system SHALL emit mineru_qa_gate_failures_total{gate_type=reading_order|ocr_quality|table_structure}

#### Scenario: GPU utilization tracking

- **WHEN** MinerU is running
- **THEN** the system SHALL emit mineru_gpu_utilization_percent, mineru_gpu_memory_used_bytes
