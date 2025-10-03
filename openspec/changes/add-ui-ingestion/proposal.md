# Change Proposal: Ingestion Management UI

## Why

Medical_KG ingests from 20+ diverse sources (ClinicalTrials.gov, PubMed, PMC, DailyMed, device registries, guidelines). Currently, ingestion requires CLI commands or direct API calls. Analysts need a visual interface to configure sources, schedule batch ingestions, monitor progress, review ingestion history, and troubleshoot failures without command-line access.

## What Changes

- Create a source catalog UI displaying all 20+ available adapters with descriptions and capabilities
- Build batch ingestion form with source-specific parameter fields (NCT IDs, PMCIDs, date ranges, etc.)
- Implement real-time ingestion progress monitoring with document-level status tracking
- Add ingestion history table with filtering, sorting, and drill-down to document details
- Provide ingestion ledger visualization showing state transitions (queued → in-progress → completed/failed)
- Create retry/rerun functionality for failed ingestions with error analysis
- Add scheduled ingestion job configuration with cron-like scheduling
- Implement PDF upload interface for manual document ingestion via MinerU pipeline
- Provide batch validation before submission (parameter format checking, duplicate detection)

## Impact

**Affected specs:** NEW `ui-ingestion` capability

**Affected code:**

- NEW `src/Medical_KG/ui/ingestion/` - React components for ingestion UI
- NEW `src/Medical_KG/ui/ingestion/SourceCatalog.tsx` - source browser
- NEW `src/Medical_KG/ui/ingestion/BatchIngestionForm.tsx` - multi-step form
- NEW `src/Medical_KG/ui/ingestion/IngestionMonitor.tsx` - progress tracking
- NEW `src/Medical_KG/ui/ingestion/IngestionHistory.tsx` - historical view
- NEW `src/Medical_KG/api/ingestion_ui.py` - API endpoints for ingestion UI
- MODIFIED `src/Medical_KG/ingestion/ledger.py` - add query methods for UI
- MODIFIED `src/Medical_KG/ingestion/registry.py` - expose adapter metadata
- NEW `src/Medical_KG/ui/ingestion/hooks/useIngestionJob.ts` - React hooks for job management
