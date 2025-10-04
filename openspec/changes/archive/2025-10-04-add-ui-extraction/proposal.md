# Change Proposal: Clinical Extraction Management UI

## Why

Medical_KG extracts structured clinical data (PICO, effects with HR/CI, adverse events, dose, eligibility criteria) from chunks using LLM+templates. Users need a UI to configure extractions, review extraction results, correct errors, validate spans, and approve data for KG ingestion without manual JSON editing.

## What Changes

- Create chunk selection interface with preview and facet-type filtering
- Build extraction configuration form with type selection (PICO/Effects/AE/Dose/Eligibility) and parameter tuning
- Implement extraction result viewer with side-by-side chunk text and structured output
- Add span highlighting showing character offsets and extracted values
- Provide manual correction UI with inline editing, span adjustment, and re-extraction
- Create extraction validation dashboard showing confidence scores, missing fields, and conflicts
- Add bulk approval workflow for reviewed extractions
- Implement extraction history and audit trail
- Provide extraction quality metrics (coverage, precision, inter-annotator agreement)

## Impact

**Affected specs:** NEW `ui-extraction` capability

**Affected code:**

- NEW `src/Medical_KG/ui/extraction/ChunkSelector.tsx`
- NEW `src/Medical_KG/ui/extraction/ExtractionConfig.tsx`
- NEW `src/Medical_KG/ui/extraction/ResultViewer.tsx`
- NEW `src/Medical_KG/ui/extraction/SpanEditor.tsx`
- NEW `src/Medical_KG/ui/extraction/ValidationDashboard.tsx`
- NEW `src/Medical_KG/api/extraction_ui.py`
- MODIFIED `src/Medical_KG/extraction/service.py` - add confidence scoring
