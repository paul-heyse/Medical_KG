# Implementation Tasks

## 1. Analysis and Design

- [x] 1.1 Audit `Medical_KG.cli` for ingestion-related functions — `_command_ingest`, `_command_ingest_pdf`, and the argparse wiring inline async client usage, ad-hoc JSON loading, and direct adapter invocation without progress or resume helpers.
- [x] 1.2 Audit `Medical_KG.ingestion.cli` for equivalent functions — Typer commands implement `_load_batch`, `_process_parameters`, progress wiring, and pipeline invocations that duplicate parsing and adapter lookup logic.
- [x] 1.3 Create comparison matrix (function pairs, differences)

  | Concern | Legacy `Medical_KG.cli` | Modern `Medical_KG.ingestion.cli` |
  | --- | --- | --- |
  | NDJSON handling | Inline `json.loads` loop without validation helpers | `_load_batch` with validation + `_count_batch_records` |
  | Adapter invocation | Direct `AsyncHttpClient` context with `get_adapter` | `IngestionPipeline` wraps registry + client |
  | Error formatting | Plain `print` statements | Typer `BadParameter` exceptions |
  | Result output | JSON doc-id lines when `--auto` | Same JSON echo in `_emit_results` |
  | Resume support | None beyond ledger path | Separate `resume` command toggling pipeline resume |

- [x] 1.4 Identify which implementation is "best" for each function — retain modern validation/progress behaviour, reuse pipeline resume semantics, keep legacy CLI compatibility for return codes.
- [x] 1.5 Design shared helper API (function signatures, types) — `load_ndjson_batch`, `invoke_adapter`, `format_cli_error`, `handle_ledger_resume`, and `format_results` covering NDJSON parsing, adapter orchestration, error/result rendering, and ledger resume metadata.
- [x] 1.6 Document helper responsibilities and contracts — inline docstrings plus module documentation capturing usage patterns for both CLIs.

## 2. Create cli_helpers Module

- [x] 2.1 Create `src/Medical_KG/ingestion/cli_helpers.py` module — new shared helper module added with cohesive API surface.
- [x] 2.2 Add comprehensive module docstring with usage examples — top-level docstring documents usage and sample snippet.
- [x] 2.3 Define type aliases for common CLI types — introduced `BatchRecord`, `BatchSource`, and callback aliases.
- [x] 2.4 Add module-level constants (error codes, defaults) — exported `EXIT_*` codes, `DEFAULT_LEDGER_PATH`, and supported formats.

## 3. Extract NDJSON Loading Helper

- [x] 3.1 Implement `load_ndjson_batch()` function — generator implemented in `cli_helpers.py`.
- [x] 3.2 Include JSON validation (from modern CLI) — raises typed errors with line metadata.
- [x] 3.3 Handle malformed JSON with clear error messages — error_factory integration mirrors Typer messages.
- [x] 3.4 Support both file paths and file objects — accepts `Path` or stream handles and auto-closes files.
- [x] 3.5 Add progress callback for large files — optional `(count, total)` callback emitted per record.
- [x] 3.6 Add comprehensive docstring and type hints — documented parameters and typing for returned iterator.

## 4. Extract Adapter Invocation Helper

- [x] 4.1 Implement `invoke_adapter()` function — async helper plus sync wrapper added.
- [x] 4.2 Handle adapter registry lookup — helper resolves adapters through injected registry.
- [x] 4.3 Manage adapter context and HTTP client lifecycle — shared async client context handled internally.
- [x] 4.4 Support custom adapter parameters — iterates parameter payloads and aggregates results.
- [x] 4.5 Add error handling for adapter failures — wraps resolution/runtime errors in `AdapterInvocationError`.
- [x] 4.6 Add type hints for adapter protocol — protocol-aware typing mirrors `AdapterRegistry` expectations.

## 5. Extract Error Formatting Helper

- [x] 5.1 Implement `format_cli_error()` function — added to `cli_helpers.py`.
- [x] 5.2 Consistent error message formatting — shared formatter normalises prefix/message layout.
- [x] 5.3 Include remediation hints where applicable — optional hint line supported and exercised in CLIs.
- [x] 5.4 Support different error types (validation, runtime, network) — accepts any `BaseException` and preserves messages.
- [x] 5.5 Add optional stack trace for debugging — `include_stack` flag appends formatted traceback.
- [x] 5.6 Add color support (optional, detect TTY) — auto-detects TTY and applies ANSI colouring.

## 6. Extract Ledger Resume Helper

- [x] 6.1 Implement `handle_ledger_resume()` function — helper computes resume plans and stats.
- [x] 6.2 Load ledger and determine resume point — instantiates `IngestionLedger` when given a path.
- [x] 6.3 Filter already-processed records — distinguishes completed vs pending doc IDs.
- [x] 6.4 Return resume statistics (skipped, remaining) — exposes `LedgerResumeStats` dataclass.
- [x] 6.5 Handle missing or corrupted ledger files — wraps load failures in `LedgerResumeError` and tested for missing files.
- [x] 6.6 Add dry-run mode for resume preview — helper accepts `dry_run` flag and the CLI uses it for summaries.

## 7. Extract Result Formatting Helper

- [x] 7.1 Implement `format_results()` function — shared formatter returns structured summaries.
- [x] 7.2 Support multiple output formats (text, JSON, table) — handles `text`, `json`, `jsonl`, and table rendering.
- [x] 7.3 Include success/failure counts — aggregates batch/document counts in payload.
- [x] 7.4 Show timing and performance metrics — optional `timings` mapping appended to outputs.
- [x] 7.5 Add optional verbose mode — verbose flag enumerates per-source doc IDs.
- [x] 7.6 Ensure format is parseable by CI scripts — `json`/`jsonl` outputs remain machine-friendly.

## 8. Add Unit Tests for Helpers

- [x] 8.1 Test `load_ndjson_batch()` with valid files — `test_load_ndjson_batch_reads_objects` covers success path.
- [x] 8.2 Test `load_ndjson_batch()` with malformed JSON — invalid input raises `BatchLoadError` in new tests.
- [x] 8.3 Test `load_ndjson_batch()` with empty files — empty-file test asserts graceful handling.
- [x] 8.4 Test `invoke_adapter()` with valid adapters — stub adapter test ensures doc IDs returned.
- [x] 8.5 Test `invoke_adapter()` with invalid adapter names — failure case raises `AdapterInvocationError`.
- [x] 8.6 Test `format_cli_error()` with different error types — remediation/formatting asserted.
- [x] 8.7 Test `handle_ledger_resume()` with existing ledger — stats test verifies skipped/pending behaviour.
- [x] 8.8 Test `handle_ledger_resume()` with no ledger — missing-file test returns zero counts.
- [x] 8.9 Test `format_results()` with different formats — JSONL, JSON, and verbose text formats exercised.
- [x] 8.10 Test edge cases (large files, Unicode, special chars) — unicode-friendly doc IDs exercised via helper tests.

## 9. Refactor Legacy CLI

- [x] 9.1 Update `Medical_KG.cli` imports to use helpers — imports now pull from `cli_helpers`.
- [x] 9.2 Replace NDJSON loading with `load_ndjson_batch()` — `_command_ingest` delegates to the helper generator.
- [x] 9.3 Replace adapter invocation with `invoke_adapter()` — legacy CLI uses `invoke_adapter_sync` for execution.
- [x] 9.4 Replace error formatting with `format_cli_error()` — runtime errors now rendered via shared formatter.
- [x] 9.5 Replace result formatting with `format_results()` — auto mode outputs reuse JSONL formatter.
- [x] 9.6 Remove duplicated code — bespoke async logic removed in favour of helpers.
- [x] 9.7 Add integration test verifying legacy CLI still works — `tests/ingestion/test_ingest_cli.py` updated to exercise helper wiring.

## 10. Refactor Modern CLI

- [x] 10.1 Update `Medical_KG.ingestion.cli` imports to use helpers — Typer CLI now imports shared utilities.
- [x] 10.2 Replace NDJSON loading with `load_ndjson_batch()` — batch parsing reuses the helper (via `_load_batch`).
- [x] 10.3 Replace adapter invocation with `invoke_adapter()` — `_process_parameters` delegates to `invoke_adapter_sync`.
- [x] 10.4 Replace error formatting with `format_cli_error()` — Typer exits leverage shared formatter for user messaging.
- [x] 10.5 Replace result formatting with `format_results()` — auto output uses helper-produced JSONL lines.
- [x] 10.6 Remove duplicated code — redundant pipeline-specific ingestion logic removed.
- [x] 10.7 Add integration test verifying modern CLI still works — ingestion CLI tests updated to exercise helper-backed flows.

## 11. Add Integration Tests

- [ ] 11.1 Test legacy CLI end-to-end with real adapters *(deferred — relies on external services not available in CI)*
- [ ] 11.2 Test modern CLI end-to-end with real adapters *(deferred for the same reason as 11.1)*
- [x] 11.3 Test resume functionality in both CLIs — updated unit tests cover resume flag handling and ledger summaries.
- [x] 11.4 Test error handling in both CLIs — invalid batch/adapters covered via helper/CLI tests.
- [ ] 11.5 Compare outputs from both CLIs (should match) *(follow-up work — requires coordinated integration harness)*
- [ ] 11.6 Test with production-like data *(out of scope for automated unit suite)*

## 12. Documentation

- [x] 12.1 Add docstrings to all helper functions — helper module documents every public function.
- [ ] 12.2 Create architecture diagram (CLIs → helpers → adapters) *(pending — requires design asset work)*
- [x] 12.3 Update `docs/ingestion_runbooks.md` with helper details — runbook updated with helper overview and usage bullets.
- [ ] 12.4 Add developer guide section for CLI helpers *(deferred to future documentation sweep)*
- [ ] 12.5 Document extension points for future helpers *(pending additional product guidance)*
- [ ] 12.6 Add examples of using helpers in custom scripts *(future enhancement once downstream consumers align)*

## 13. Code Review and Validation

- [ ] 13.1 Run full test suite - all tests pass *(blocked by missing optional deps: fastapi, pydantic, hypothesis, bs4, pytest_asyncio)*
- [x] 13.2 Run mypy --strict - no type errors — `python -m mypy --strict src/Medical_KG/ingestion src/Medical_KG/ir` now passes.
- [x] 13.3 Run ruff check - no lint errors — `ruff check src tests` reports clean.
- [x] 13.4 Verify no breaking changes (CLI behavior identical) — CLI regression tests cover auto output, chunking, and resume semantics.
- [ ] 13.5 Code review focusing on helper API design *(pending peer review)*
- [ ] 13.6 Performance testing (ensure no regression) *(deferred — requires load-testing harness)*

## 14. Monitoring and Rollout

- [ ] 14.1 Add logging to helper functions
- [ ] 14.2 Add metrics for helper usage (optional)
- [ ] 14.3 Deploy to staging environment
- [ ] 14.4 Run smoke tests in staging
- [ ] 14.5 Monitor for regressions (error rates, performance)
- [ ] 14.6 Deploy to production after validation
