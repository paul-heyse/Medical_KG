# Repository Optimization Opportunities

## Summary
- The codebase has multiple parallel entrypoints and helper layers that solve the same problem differently; consolidating them onto shared, extensible surfaces will make day-to-day operations more predictable and easier to extend.
- Several core services (ingestion pipeline, ledger, configuration loader) are built around bespoke helpers that scale poorly or rely on implicit string conventions; upgrading them to streaming-first, schema-driven components will improve robustness and long-term maintainability.
- Optional-dependency and typing guardrails are uneven across packages, leaving observability and adapter code vulnerable to import drift and undocumented gaps; tightening those checks provides flexible patterns instead of ad hoc fixes.

## Recommendations

### 1. Consolidate CLI entrypoints on the Typer application
**Opportunity.** The legacy `argparse` CLI proxies ingestion commands by shelling into the Typer app while reimplementing PDF/mineru/post-processing commands separately, so behavior drifts and argument handling differs depending on which path code uses.【F:src/Medical_KG/cli.py†L220-L307】 Meanwhile the Typer ingestion CLI already centralises adapter discovery, batching, schema validation, and progress reporting in a structured, reusable way.【F:src/Medical_KG/ingestion/cli.py†L31-L156】

**Proposal.** Move the remaining PDF and configuration commands into Typer subapps, exposing a single `med` entrypoint that shares option parsing, logging, and help text. Provide a thin compatibility shim for scripts that still import `Medical_KG.cli:main`, but have it call the Typer app directly instead of re-parsing arguments.

**Benefits.** A single CLI stack reduces drift, makes it easier to add cross-cutting flags (logging level, dry-run), and eliminates custom parsing hacks (like manually stashing `argv`) that make future enhancements brittle.【F:src/Medical_KG/cli.py†L282-L298】

### 2. Make the ingestion pipeline streaming-first and composable
**Opportunity.** `IngestionPipeline.run_async` eagerly materialises every `doc_id` before returning, so large adapter runs accumulate all results in memory even though `iter_results` already streams documents lazily.【F:src/Medical_KG/ingestion/pipeline.py†L71-L120】 Downstream orchestration code must therefore choose between eager lists or rolling its own streaming loop.

**Proposal.** Promote `iter_results` to the primary execution API by yielding structured events (e.g., `PipelineEvent` dataclasses for `started`, `document_completed`, `failed`). Keep `run`/`run_async` as convenience wrappers that consume the iterator but document their higher memory usage. Wire progress reporting, telemetry, and retries through the event stream so batch jobs can fan-out work without bespoke adapters.

**Benefits.** A first-class streaming contract makes backpressure manageable, avoids one-off loaders that read entire NDJSON files at once, and creates a single place to add metrics or resume checkpoints as the platform grows.【F:src/Medical_KG/ingestion/pipeline.py†L51-L88】

### 3. Introduce a ledger state machine with compaction support
**Opportunity.** The JSONL ledger loads every historical entry into `_latest` at startup and exposes states as free-form strings; long-running ingest environments will accumulate hundreds of thousands of rows and rely on implicit literals like `"pdf_ir_ready"` that are sprinkled across services.【F:src/Medical_KG/ingestion/ledger.py†L28-L91】【F:src/Medical_KG/pdf/service.py†L169-L183】

**Proposal.** Model ledger transitions with an explicit `Enum` (or TypedDict schema) so each state change is validated and discoverable. Add periodic compaction—either a snapshot file or tail-only iterator—so initialization cost stays flat even as history grows. Emit structured audit records (timestamp, adapter params, error types) instead of plain strings to assist triage.

**Benefits.** A state machine and compaction pipeline let new adapters plug into ingestion without hard-coding magic strings, while keeping ledger memory usage predictable and enabling richer operational dashboards.

### 4. Replace the bespoke configuration validator with a proven schema engine
**Opportunity.** `ConfigValidator` partially reimplements JSON Schema (handing refs, enums, numeric ranges) and has to be updated whenever configs evolve.【F:src/Medical_KG/config/manager.py†L66-L159】 Maintaining this forked validator increases risk that new keywords or annotations silently skip validation.

**Proposal.** Swap the home-grown validator for `jsonschema` (already vendored for CLI validation) or `pydantic` models that compile the schema once and provide typed accessors. Document which schema version the repo targets and add regression tests that fail fast when unsupported constructs appear.

**Benefits.** Leaning on a dedicated library reduces surface area, improves error messages for operators, and opens the door to schema-driven tooling (auto-complete, diffing) instead of bespoke checks.【F:src/Medical_KG/config/manager.py†L204-L270】

### 5. Standardise optional dependency handling and tighten typing coverage
**Opportunity.** Optional dependency helpers currently raise generic `ModuleNotFoundError` messages and the project silences mypy across wide swaths of the codebase, including observability and retrieval packages.【F:src/Medical_KG/utils/optional_dependencies.py†L329-L420】【F:pyproject.toml†L159-L204】 This invites one-off fixes every time dependencies move or when a new module needs typing exemptions.

**Proposal.** Introduce a structured `MissingDependencyError` that captures the feature, install hint, and optional extras group, and replace generic `ModuleNotFoundError` strings with it. Incrementally shrink the `ignore_errors` lists by adding typed protocol shims or stub packages, ensuring new code cannot hide behind global suppressions. Document the dependency matrix in the developer guide so contributors know which extras to install for each subsystem.

**Benefits.** Contributors receive actionable guidance instead of raw import errors, CI gains earlier signal when types drift, and optional features become plug-and-play rather than bespoke troubleshooting exercises.

### 6. Expose richer telemetry from the async HTTP client
**Opportunity.** The shared `AsyncHttpClient` handles retries and rate limiting internally but only records high-level counters and lacks structured hooks for logging retry attempts, saturation, or payload metadata.【F:src/Medical_KG/ingestion/http_client.py†L115-L195】 Teams that need custom tracing or per-host instrumentation currently duplicate logic around this client.

**Proposal.** Add callback hooks (e.g., `on_request`, `on_retry`, `on_backoff`) or an event emitter interface that adapters can subscribe to for structured logs and metrics. Capture limiter queue times and expose them via Prometheus histograms so saturation is observable without patching the client.

**Benefits.** Shared telemetry primitives prevent each adapter from building one-off wrappers, make throttling issues diagnosable, and keep resilience policies consistent across ingestion surfaces.
