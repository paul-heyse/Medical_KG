# Changelog

## [Unreleased]

### Removed

- Removed the deprecated `IngestionPipeline.run_async_legacy()` wrapper, related environment toggles, and legacy telemetry labels.
- Deleted CLI migration tooling and helper scripts now that the unified CLI is fully adopted.
- Removed the final ledger compatibility shims (`LedgerState.LEGACY`, string coercion helpers) and introduced enum-only validation tooling.
- Deleted the remaining legacy-focused regression tests and fixtures so the suite
  reflects the streaming-first API surface.
- Retired IR builder fallback payload coercion; `IrBuilder.build()` and
  `IRValidator.validate_document()` now require typed payloads, and
  `DocumentIR` exposes structured `metadata` for downstream consumers while
  rejecting synthesized raw data.

### Documentation

- Documented the legacy wrapper removal across runbooks, contributor guidance, and operations checklists.
- Archived CLI migration roadmaps and linked the documentation archive from active guides.
- Added typed IR construction examples and clarified metadata validation requirements in the IR guide.

## [2.0.0] - 2025-10-03

### Removed

- Deprecated ingestion CLI entry points, including the `med ingest-legacy` command and flag translation layer.

### Changed

- Bumped the package version to `2.0.0` to signal the breaking removal of the deprecated CLI.
- Unified CLI invocation is now the sole supported path: use `med ingest <adapter> [options]`.

### Migration Guidance

- Before: `med ingest --source pubmed --batch file.ndjson --resume`
- After: `med ingest pubmed --batch file.ndjson --resume`
- See `docs/ingestion_runbooks.md` for the updated command reference and `ops/release/2025-10-remove-legacy-ingestion-cli.md` for rollback instructions.
