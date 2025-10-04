# Legacy Debt Retirement & Optimization Scopes

This briefing identifies the high-leverage change scopes required to finish the migration away from legacy ingestion, configuration,
and telemetry code paths. It builds on the `refactor-ingestion-typedicts` follow-up work (`FOLLOWUP_SUMMARY.md`) and the repository
optimization proposals package. Each scope is intended to be delivered as a dedicated OpenSpec change so we can phase removals,
control risk, and unlock measurable reductions in maintenance cost.

## Portfolio View

| Scope ID | Theme | Core Outcome | Effort | Dependencies |
|----------|-------|--------------|--------|--------------|
| `remove-run-async-legacy` | Pipeline | Delete deprecated ingestion pipeline wrappers and counters | 3-4 days | `refactor-ingestion-pipeline-streaming` deployed |
| `purge-legacy-ledger-compat` | Ledger | Finalize enum state machine and drop string-based fallbacks | 4-5 days | `refactor-ledger-state-machine` implementation |
| `replace-config-validator-jsonschema` | Configuration | Remove bespoke validator + resurrected legacy tests, adopt jsonschema fully | 4-5 days | None (blocked patch queued as `codex16.patch`) |
| `retire-ir-legacy-fallbacks` | IR Layer | Require typed payloads in IR builder, drop legacy coercion | 3 days | Typed payload proposals (Phases 1-3) |
| `remove-legacy-ingestion-tooling` | Tooling | Delete CLI migration scripts & env flags tied to legacy commands | 2 days | Unified CLI adoption metrics ≥95% |
| `standardize-optional-dependency-handling` | Optional deps | Collapse historic shims, enforce `MissingDependencyError` contract | 4 days | Proposal `standardize-optional-dependencies` |
| `normalize-http-telemetry` | Telemetry | Replace noop metrics + bespoke registries with unified hooks | 5 days | `add-http-client-telemetry` foundation |
| `clean-legacy-test-surfaces` | QA | Remove fixtures/tests targeting legacy paths, backfill coverage | 3 days | Scopes above completed |

## Scope Details

### 1. `remove-run-async-legacy`

**Why now**: `IngestionPipeline.run_async_legacy()` remains in production as a compatibility shim despite the streaming rewrite.
It preserves the historic return signature, emits deprecation warnings, and increments dedicated counters that we still ship in
telemetry. The method is marked for removal in the streaming design doc after the migration window, but the code has not yet been
scheduled for deletion.

**Key actions**:

- Delete `IngestionPipeline.run_async_legacy()` and `_log_legacy_usage()`; convert remaining callers to `stream_events()`/`run_async()`.
- Remove legacy consumption mode handling (`consumption_mode="run_async_legacy"`) from events/emission logic.
- Drop environment toggles that silence legacy warnings (e.g., `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION`).
- Update docs and runbooks to reference only the streaming API.

**Deliverables & Metrics**:

- Zero references to `run_async_legacy` in `src/` and `tests/`.
- Telemetry dashboard confirms no "legacy" counters remain.
- `pytest tests/ingestion/test_pipeline.py` passes without legacy fixtures.

### 2. `purge-legacy-ledger-compat`

**Why now**: The ledger still exposes a `LedgerState.LEGACY` enum value and migration scripts that coerce string-based histories into
the new state machine. Once the state machine proposal lands, we should prune the compatibility layer to prevent divergent behavior
and reduce boot-time translation overhead.

**Key actions**:

- Remove the `LEGACY` placeholder from `LedgerState` and delete coercion helpers that accept arbitrary strings.
- Drop `scripts/migrate_ledger_to_state_machine.py` once roll-forward migrations complete.
- Rewrite fixtures/tests (`tests/ingestion/test_pipeline.py`, `tests/test_ingestion_ledger_state_machine.py`) to seed enum-based
states only.
- Compact historical ledgers in staging/prod to strip legacy markers.

**Deliverables & Metrics**:

- Ledger initialization shows 0 conversions from string → enum in telemetry.
- All ledger audit events use the enum type; mypy strict passes with no `Literal["legacy"]` references.
- Operational runbooks updated with the final enum-only lifecycle.

### 3. `replace-config-validator-jsonschema`

**Why now**: The `codex16.patch` rejects demonstrate that the repository still contains custom `LegacyValidator` logic, YAML config
snapshots, and CI wiring that expect the bespoke schema validator. Reapplying that patch manually has high drift risk. Instead, we
should treat the jsonschema migration as a dedicated scope that deletes the entire legacy path and refreshes workflows.

**Key actions**:

- Land the jsonschema-backed validator (`tests/config/test_schema_validator.py` already anticipates parity between legacy and new
validators) and delete `LegacyValidator` implementations plus policy YAML duplication.
- Update `.github/workflows/ci.yml` and `.pre-commit-config.yaml` to rely on jsonschema checks.
- Remove deprecated config files (`config-dev.yaml`, `config-prod.yaml`, etc.) that exist solely to support the old validator.
- Document schema versioning and migration steps in `docs/configuration.md`.

**Deliverables & Metrics**:

- `grep -r "LegacyValidator"` returns no matches.
- Config validation jobs run `jsonschema` exclusively; CI green.
- Configuration docs explain schema evolution + version pinning.

### 4. `retire-ir-legacy-fallbacks`

**Why now**: The IR builder still advertises "legacy behaviour" when callers omit the typed `raw` payload. After the typed payload
follow-up work, this fallback becomes dead weight that prevents us from depending on structured metadata downstream.

**Key actions**:

- Require `Document.raw` to be one of the typed payload unions when constructing IR nodes; raise explicit errors otherwise.
- Delete fallback coercion paths in `src/Medical_KG/ir/builder.py` that synthesize placeholder payloads.
- Update adapters/tests to always pass typed payloads into the IR layer.
- Add strict mypy enforcement for `DocumentIRBuilder` inputs.

**Deliverables & Metrics**:

- IR builder API no longer mentions legacy behavior; docstrings updated.
- `mypy --strict src/Medical_KG/ir` passes with no `Any` leaks from payload coercion.
- Integration tests confirm typed payloads propagate end-to-end.

### 5. `remove-legacy-ingestion-tooling`

**Why now**: We still ship helper scripts under `scripts/cli_migration/` and operations guides that reference legacy CLI commands.
With Phase 3 of the CLI unification complete, these artifacts encourage backsliding and increase maintenance work when updating
flags or documentation.

**Key actions**:

- Delete migration-only scripts (`scripts/cli_migration/*.py`, `scripts/check_streaming_migration.py`) and archive the release playbook.
- Remove references to legacy commands from `CLI_UNIFICATION_ROADMAP.md`, `CLI_UNIFICATION_SUMMARY.md`, and ops runbooks.
- Purge env variables and warnings tailored to the migration (e.g., "legacy command removed" macros).
- Announce tooling retirement in release notes and contributor guides.

**Deliverables & Metrics**:

- Repo contains zero executable tooling referencing legacy CLI commands.
- Docs reference only the unified CLI; search for "legacy CLI" limited to historical archives.
- Release checklist updated to exclude migration steps.

### 6. `standardize-optional-dependency-handling`

**Why now**: Optional dependency handling evolved organically. Some modules still use ad-hoc `try/except ImportError` blocks or
`optional_import` helpers that predate `MissingDependencyError`. Consolidating on a single protocol removes branching logic and
ensures consistent contributor guidance.

**Key actions**:

- Audit `src/Medical_KG/**` for manual optional import patterns and replace them with `MissingDependencyError` + protocol shims.
- Delete deprecated helpers in `utils/optional_dependencies.py` once call sites migrate.
- Add lint rule or pre-commit hook to block new ad-hoc optional import code.
- Refresh contributor docs with the standardized pattern.

**Deliverables & Metrics**:

- Optional dependency module exposes a minimal public API; legacy helpers removed.
- `rg "optional_import"` shows only sanctioned entry points.
- Pre-commit fails when `ImportError` suppression without `MissingDependencyError` is introduced.

### 7. `normalize-http-telemetry`

**Why now**: The HTTP client currently registers telemetry handlers dynamically and falls back to `_NoopMetric` placeholders. After
shipping the structured telemetry proposal we should consolidate metrics behind a single registry, expose Prometheus integration
as the default, and eliminate per-host callback plumbing that duplicates logic.

**Key actions**:

- Remove the `_NoopMetric` scaffolding and unused Prometheus discovery logic from `ingestion/http_client.py`.
- Centralize telemetry subscription in `ingestion/telemetry.py` with a stable interface.
- Provide configuration knobs for enabling/disabling metrics instead of implicit detection.
- Update adapter instrumentation to rely on the shared registry.

**Deliverables & Metrics**:

- HTTP client exposes a single telemetry registration path; no `_NoopMetric` class remains.
- Prometheus metrics enabled via config flag with documented defaults.
- Benchmark shows ≤2% overhead compared to current implementation.

### 8. `clean-legacy-test-surfaces`

**Why now**: Several test modules still construct legacy artifacts (e.g., `legacy-ledger.jsonl`, `LegacyValidator` parity assertions)
that will fail once the scopes above land. Cleaning these proactively reduces drift and keeps CI focused on supported flows.

**Key actions**:

- Delete or rewrite tests under `tests/ingestion/` and `tests/config/` that depend on legacy helpers.
- Introduce new smoke tests that exercise the streaming pipeline, enum-only ledger, jsonschema validation, and typed IR flow.
- Purge fixtures/data files solely referenced by legacy tests.

**Deliverables & Metrics**:

- Test suite contains no references to "legacy" outside archived fixtures.
- Coverage reports confirm replacement tests keep ≥ the previous coverage for ingestion/config modules.
- CI runtime decreases due to removal of redundant legacy scenarios.

## Recommended Sequencing

1. Execute `remove-run-async-legacy` immediately after confirming zero production usage of the wrapper.
2. In parallel, deliver `replace-config-validator-jsonschema` to unlock CI modernization and unblock `codex16.patch` fallout.
3. Complete typed payload follow-ups, then tackle `retire-ir-legacy-fallbacks` and `clean-legacy-test-surfaces` together.
4. Finish infrastructure scopes (`purge-legacy-ledger-compat`, `normalize-http-telemetry`, `standardize-optional-dependency-handling`).
5. Close with documentation/tooling cleanup (`remove-legacy-ingestion-tooling`).

Following this roadmap removes the final compatibility shims, aligns every surface with the streaming + typed architecture, and
prevents new code from reintroducing legacy behavior.
