# Implementation Tasks

## 1. Chunk Selection

- [ ] 1.1 Create `ChunkSelector` component with search and filter
- [ ] 1.2 Add chunk preview cards showing text snippet, facet type, and metadata
- [ ] 1.3 Implement multi-select with checkboxes and "Select All" option
- [ ] 1.4 Add facet type filter (PICO, Effects, AE, Dose, Eligibility)
- [ ] 1.5 Create bulk import from document or retrieval results

## 2. Extraction Configuration

- [ ] 2.1 Build `ExtractionConfig` form with extraction type selection
- [ ] 2.2 Add parameter tuning fields (temperature, confidence threshold, span strictness)
- [ ] 2.3 Create model selection dropdown (if multiple extraction models available)
- [ ] 2.4 Implement "Test on Sample" feature running extraction on 1 chunk for validation
- [ ] 2.5 Add batch size configuration for large extraction jobs

## 3. Result Viewer

- [ ] 3.1 Create `ResultViewer` with side-by-side layout (chunk text | extracted data)
- [ ] 3.2 Implement span highlighting with color coding by field type
- [ ] 3.3 Add hover tooltips on spans showing extracted value and confidence
- [ ] 3.4 Create JSON tree view for structured extraction output
- [ ] 3.5 Add navigation controls for multi-chunk results (prev/next)

## 4. Span Editor

- [ ] 4.1 Build `SpanEditor` enabling text selection to adjust span boundaries
- [ ] 4.2 Add inline value editing for extracted fields
- [ ] 4.3 Implement "Re-extract" button with updated span constraints
- [ ] 4.4 Create span conflict resolution UI (overlapping spans)
- [ ] 4.5 Add manual span creation for missed extractions

## 5. Validation Dashboard

- [ ] 5.1 Create extraction quality metrics display (coverage, confidence distribution)
- [ ] 5.2 Build validation table showing all extractions with approval status
- [ ] 5.3 Add filtering by confidence level, missing fields, conflicts
- [ ] 5.4 Implement bulk approval workflow with review checkpoints
- [ ] 5.5 Create export of validated extractions to KG write format

## 6. Backend API

- [ ] 6.1 Extend `/extract/*` endpoints to include confidence scores
- [ ] 6.2 Add `/api/extraction/chunks` GET endpoint for chunk selection
- [ ] 6.3 Create `/api/extraction/batch` POST endpoint for multi-chunk extractions
- [ ] 6.4 Implement `/api/extraction/validate` POST endpoint for approval workflow
- [ ] 6.5 Add `/api/extraction/history` GET endpoint for audit trail

## 7. Testing & Documentation

- [ ] 7.1 Write unit tests for extraction components
- [ ] 7.2 Add integration tests for extraction API with validation
- [ ] 7.3 Create E2E tests for chunk select → extract → validate → approve workflow
- [ ] 7.4 Document extraction UI in `docs/ui_extraction.md`
