# Repository Review

## Quality Snapshot
- `pytest -q` is currently unavailable in this container because the managed virtual environment (`.venv`) is missing. Recreating it with the documented micromamba workflow is a prerequisite for validating the suite locally. 【d51a02†L1-L2】

## Fix Implemented
- Added a public `run_async` entrypoint to the ingestion pipeline so orchestration code that already owns an asyncio event loop can execute adapters without triggering `asyncio.run` recursion errors; the synchronous wrapper now delegates to the shared implementation and a regression test exercises the coroutine path. 【F:src/Medical_KG/ingestion/pipeline.py†L51-L84】【F:tests/ingestion/test_pipeline.py†L105-L125】

## Recommended Improvements

### Ingestion Workflow
- Stream NDJSON batches in the CLI instead of calling `list(_load_batch(...))`; large re-ingestion campaigns will otherwise read the full file into memory before dispatching any work. Replacing the eager conversion with a simple iterator (or chunked generator) would make `med ingest --batch` scale to millions of records. 【F:src/Medical_KG/ingestion/cli.py†L25-L68】
- `IngestionPipeline.run_async` still materialises every adapter result before returning. Exposing an async iterator (e.g., `async def iter_results`) would allow downstream code to process documents incrementally, reduce peak memory, and wire up streaming telemetry for long-running adapters. 【F:src/Medical_KG/ingestion/pipeline.py†L62-L104】

### Ledger Durability & Diagnostics
- The JSONL-backed ledger eagerly loads every historical entry into `_latest` during initialisation and never compacts the log; when the file grows into hundreds of thousands of rows the startup cost and memory footprint will spike. Introducing periodic compaction (e.g., checkpoint files) or lazy iteration over the tail of the ledger would keep resume-capable pipelines fast. 【F:src/Medical_KG/ingestion/ledger.py†L28-L87】
- Consider persisting richer failure metadata (HTTP status, adapter parameters) so operations can triage ingest incidents without rerunning the adapter. The current ledger only captures a stringified exception and the doc ID. 【F:src/Medical_KG/ingestion/ledger.py†L58-L78】

### HTTP Client Resilience
- `AsyncHttpClient` manages `AsyncClientProtocol` lifetime manually; adding `__aenter__/__aexit__` (and a synchronous context manager wrapper) would let adapters and tests scope network resources with `async with AsyncHttpClient(...)` instead of remembering to call `aclose()`. 【F:src/Medical_KG/ingestion/http_client.py†L101-L180】
- Rate limiting and retries are host-wide, but there is no visibility into throttle decisions. Emitting structured logs or additional Prometheus metrics for limiter saturation would simplify debugging slow pipelines. 【F:src/Medical_KG/ingestion/http_client.py†L131-L159】

### Configuration Platform
- `ConfigValidator` re-implements a sizeable subset of JSON Schema validation; replacing it with the `jsonschema` library (or at least documenting the supported keyword subset) would reduce maintenance risk and ensure new schema constructs fail loudly instead of silently skipping checks. 【F:src/Medical_KG/config/manager.py†L40-L118】
- The configuration gauges expose version metadata but never clear old label values when deployments roll back. Calling `CONFIG_INFO.clear()` before setting the new values would prevent stale metrics for superseded versions. 【F:src/Medical_KG/config/manager.py†L16-L39】

### Observability & Optional Dependencies
- `build_counter`/`build_histogram` still suppress import errors with `# type: ignore`; shipping minimal stub modules (or updating `py.typed` packages) would let us delete the suppressions and ensure mypy surfaces real typing regressions in observability code. 【F:src/Medical_KG/utils/optional_dependencies.py†L329-L359】
- Several optional dependency accessors (`get_httpx_module`, `build_redis_client`, `load_locust`) raise bare `ModuleNotFoundError` messages. Wrapping them in a custom exception that links to installation docs would give operators clearer remediation steps. 【F:src/Medical_KG/utils/optional_dependencies.py†L362-L389】

### Documentation & Runbooks
- The ingestion operations runbook predates the typed response wrappers—updating it with the new `JsonResponse/TextResponse/BytesResponse` helpers (and linking to the typed contracts guide) would keep on-call engineers aligned with the current abstractions. 【F:docs/ingestion_runbooks.md†L1-L29】【F:src/Medical_KG/ingestion/http_client.py†L52-L118】
- The typed-contracts guide is comprehensive, but adding a short checklist that maps each adapter family to its canonical payload unions would help reviewers confirm new adapters hook into the correct TypedDict mixins. 【F:docs/ingestion_typed_contracts.md†L1-L120】【F:src/Medical_KG/ingestion/types.py†L17-L118】
# Repository Review – February 2025

## Addressed Issue
- Hardened the ingestion Typer CLI batch loader by importing the missing `json` module and validating each NDJSON row. Malformed JSON or non-object entries now surface as actionable `BadParameter` errors instead of crashing at runtime, and new tests pin the behavior.【F:src/Medical_KG/ingestion/cli.py†L3-L80】【F:tests/ingestion/test_ingestion_cli.py†L1-L155】

## Recommended Improvements
1. **Defensive dossier formatting** – ✅ Completed in `fix-ruff-config-defensive-formatting`. `BriefingFormatter` now falls back to sensible defaults ("Untitled Briefing", "Untitled Section", citation ID "Unknown", count `0`) and guards every section/item/citation lookup so partial payloads no longer raise `KeyError`. Additional briefing tests cover these cases.【F:src/Medical_KG/briefing/formatters.py†L1-L154】【F:tests/briefing/test_formatters.py†L1-L170】
2. **Unify ingestion CLIs** – ✅ Completed via the CLI unification rollout; see the archived plan in `docs/archive/cli_unification/` for historical context.
3. **Modernize Ruff configuration** – ✅ Completed in `fix-ruff-config-defensive-formatting`. Ruff lint configuration now lives under `[tool.ruff.lint]`, eliminating the extend-select deprecation warning on every lint run.【F:pyproject.toml†L150-L155】
4. **Document lint/type overrides** – Large `mypy` ignore blocks (e.g., the blanket `ignore_errors` for `Medical_KG.briefing.*` and `retrieval.*`) make it harder to track real typing debt. Audit these overrides and replace them with targeted fixes or module-level TODO comments so future contributors understand the remaining gaps.【F:pyproject.toml†L164-L195】

## Suggested Follow-Up Tests
- Extend the Typer CLI test suite with cases for the recommended dossier formatter guards and any future ingestion CLI consolidation to ensure regressions are caught early.【F:tests/ingestion/test_ingestion_cli.py†L1-L155】
