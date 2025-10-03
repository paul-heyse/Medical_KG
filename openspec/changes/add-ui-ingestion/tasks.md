# Implementation Tasks

## 1. Source Catalog

- [ ] 1.1 Create `SourceCatalog` component displaying grid of available source adapters
- [ ] 1.2 Add source metadata endpoint `/api/ingestion/sources` returning adapter capabilities
- [ ] 1.3 Implement source card with icon, name, description, example parameters, and "Ingest" button
- [ ] 1.4 Add filtering by source category (literature, clinical trials, guidelines, ontologies, devices)
- [ ] 1.5 Create source detail modal with full documentation and parameter schema

## 2. Batch Ingestion Form

- [ ] 2.1 Build multi-step form wizard with source selection → parameter input → validation → submission
- [ ] 2.2 Create dynamic parameter fields based on adapter schema (text inputs, date pickers, file uploads)
- [ ] 2.3 Add bulk input modes (CSV upload, NDJSON paste, textarea with line-separated IDs)
- [ ] 2.4 Implement client-side validation (NCT format, PMCID format, date ranges, etc.)
- [ ] 2.5 Add preview step showing parsed parameters and estimated document count
- [ ] 2.6 Create idempotency key generation and display

## 3. Progress Monitoring

- [ ] 3.1 Build `IngestionMonitor` component with real-time WebSocket updates
- [ ] 3.2 Display overall job progress bar and document-level status grid
- [ ] 3.3 Show per-document state (queued → fetching → parsing → validating → writing → done/failed)
- [ ] 3.4 Add elapsed time, estimated remaining time, and throughput metrics
- [ ] 3.5 Implement pause/resume/cancel controls for active ingestion jobs
- [ ] 3.6 Create error summary panel showing failed documents with expandable error details

## 4. Ingestion History

- [ ] 4.1 Create `IngestionHistory` table component with pagination and sorting
- [ ] 4.2 Display columns: job ID, source, timestamp, document count, success rate, duration, status
- [ ] 4.3 Add filters for date range, source type, status (completed/failed/partial)
- [ ] 4.4 Implement row expansion showing document-level details
- [ ] 4.5 Add bulk actions (retry failed, export ledger, delete job)
- [ ] 4.6 Create export functionality (CSV, NDJSON) for ingestion reports

## 5. Scheduled Ingestion

- [ ] 5.1 Build scheduled job configuration form with cron expression builder
- [ ] 5.2 Create visual cron editor (daily/weekly/monthly presets + custom)
- [ ] 5.3 Add job recurrence calendar preview showing next 10 run times
- [ ] 5.4 Implement scheduled job list with enable/disable toggle
- [ ] 5.5 Create job run history view linked to ingestion history

## 6. Backend API

- [ ] 6.1 Add `/api/ingestion/sources` endpoint returning adapter metadata
- [ ] 6.2 Implement `/api/ingestion/jobs` POST endpoint for job submission
- [ ] 6.3 Create `/api/ingestion/jobs/{job_id}` GET endpoint for job status
- [ ] 6.4 Add `/api/ingestion/jobs/{job_id}/documents` GET endpoint for document-level details
- [ ] 6.5 Implement `/api/ingestion/history` GET endpoint with filtering and pagination
- [ ] 6.6 Create WebSocket `/ws/ingestion/{job_id}` for real-time progress updates
- [ ] 6.7 Add `/api/ingestion/jobs/{job_id}/retry` POST endpoint for failed document retry

## 7. Testing & Documentation

- [ ] 7.1 Write unit tests for ingestion components (80%+ coverage)
- [ ] 7.2 Add integration tests for ingestion API endpoints
- [ ] 7.3 Create E2E tests for full ingestion workflow (source select → submit → monitor → review)
- [ ] 7.4 Document ingestion UI in `docs/ui_ingestion.md` with screenshots
- [ ] 7.5 Add Storybook stories for ingestion form and monitoring components
