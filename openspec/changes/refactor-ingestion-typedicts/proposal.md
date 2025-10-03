# Refactor Ingestion TypedDicts for Adapter-Specific Contracts

## Why
- The ingestion layer centralizes heterogeneous document payloads in a monolithic `DocumentRaw` union that masks adapter-level schema guarantees and forces pervasive `typing.cast` usage.
- Optional metadata is rarely annotated explicitly, leaving developers unsure which keys are required and causing silent schema drift between adapters.
- Static analysis (`mypy --strict`) emits noisy warnings and suppressions because helper utilities and downstream components cannot reason about the actual payload shape per adapter family.
- Continued growth of ingestion sources will compound these issues, making it harder to onboard contributors and to catch data quality regressions before runtime.

## What Changes
- Introduce reusable TypedDict mixins (e.g., identifiers, provenance, revision metadata) and replace broad `total=False` unions with explicit `NotRequired` annotations.
- Define dedicated adapter payload aliases for terminology, literature, clinical, and guideline ingest paths, exposing only the keys that each adapter emits.
- Update ingestion adapters, shared helpers (`src/Medical_KG/ingestion/types.py`, `adapters/base.py`, `ledger.py`), and IR integration points (`src/Medical_KG/ir/models.py`, `builder.py`, `validator.py`) to rely on the refined union instead of `DocumentRaw`.
- Tighten the type of `Document.raw` and related helpers to the new union so downstream consumers and tests benefit from stricter static guarantees.
- Refresh documentation, examples, and tests (unit, integration, and chaos scripts) to reflect the new payload contracts and to ensure coverage for optional fields and failure modes.

## Impact
- **Affected specs:** `specs/ingestion/spec.md` (via delta `openspec/changes/refactor-ingestion-typedicts/specs/ingestion/typedict-refactor.md`).
- **Affected code:** Primary touch points include `src/Medical_KG/ingestion/types.py`, `src/Medical_KG/ingestion/adapters/*`, `src/Medical_KG/ingestion/ledger.py`, `src/Medical_KG/ir/{models,builder,validator}.py`, and ingestion-related tests under `tests/ingestion/` and `tests/ir/`.
- **Tooling:** `mypy --strict` across `src/Medical_KG/ingestion` (and dependent IR modules) must pass without new ignores; `pytest -q` remains the regression gate; `ops/chaos/chaos_tests.sh` should be re-run if payload format changes interact with fault-injection scenarios.
- **Stakeholders:** Ingestion engineering group, IR maintainers, QA, and anyone coordinating with active type-safety initiatives (`update-type-safety-*`, `add-type-safety`).

## Detailed Plan
### Phase 1 – Payload Inventory & Schema Mapping (1-2 days)
- Audit all usages of `DocumentRaw` and related TypedDicts with `rg` and static analysis to catalogue required vs optional fields per adapter.
- Map common fields (identifiers, timestamps, provenance, canonical text) that can be abstracted into mixins; document gaps or inconsistencies.
- Validate findings with adapter owners and note any in-flight work (e.g., `update-type-safety-ingestion-base`) that might conflict.

### Phase 2 – Type Definition Overhaul (2-3 days)
- Author mixin TypedDicts in `src/Medical_KG/ingestion/types.py` for shared traits; ensure names are stable and well-documented.
- Create adapter-specific payload aliases that inherit from relevant mixins and annotate optional keys with `typing.NotRequired` (Python 3.11) or `typing_extensions.NotRequired`.
- Update the central payload union (exported for downstream use) and remove deprecated aliases; provide migration notes in module docstrings.
- Add `mypy`-friendly helper functions or protocols where runtime polymorphism is required.

### Phase 3 – Adapter & Consumer Migration (3-4 days)
- Refactor terminology, literature, clinical, and guideline adapters sequentially to emit the new TypedDicts; remove explicit casts and unreachable conditionals.
- Update `Document.raw`, the ingestion ledger, and adapter base classes to accept the refined union; adjust validation paths in `ir/builder.py` and `ir/validator.py` accordingly.
- Align tests (`tests/ingestion/*`, `tests/ir/*`) and fixtures with the new payload signatures; add targeted cases for optional metadata being present/absent.
- Coordinate with parallel changes (e.g., UI ingestion features) to ensure they either consume the refined types or are updated in lockstep.

### Phase 4 – Validation, Documentation, and Rollout (1-2 days)
- Run `mypy --strict src/Medical_KG/ingestion src/Medical_KG/ir` and `pytest -q`; resolve regressions and update suppression lists if legacy modules cannot yet adopt the new types.
- Execute `ops/chaos/chaos_tests.sh` in staging environments to confirm resilience under new payload shapes.
- Update developer docs (README sections, onboarding guides) to outline adapter payload expectations and mixin usage.
- Communicate the change to ingestion stakeholders, highlighting migration steps for any downstream consumers of `Document.raw`.

## Out of Scope
- Introducing runtime schema validation frameworks (e.g., Pydantic) or switching to dataclasses for payload modeling.
- Modifying storage or transport formats outside the ingestion layer (e.g., message queues, persistence schemas).
- Broad refactors of non-ingestion services, except where they directly couple to `Document.raw`.

## Risks & Mitigations
- **Schema Drift:** Unnoticed discrepancies between documented and actual payloads could break consumers. Mitigation: comprehensive inventory, updated tests, and cross-team reviews.
- **Parallel Changes:** Multiple active type-safety changes might conflict. Mitigation: coordinate via `openspec list`, stagger merges, and rebase frequently.
- **Runtime Regressions:** Tightened types may surface hidden assumptions. Mitigation: exercise integration and chaos tests, monitor logs during rollout.
- **Developer Adoption:** New mixins may be misused. Mitigation: add clear module docstrings, examples, and reviewer checklist items.

## Dependencies & Coordination
- Sync with `update-type-safety-core-services` and `update-type-safety-ingestion-base` owners to avoid duplicate type definitions.
- Ensure any ongoing UI ingestion efforts (`add-ui-ingestion`, `add-ui-dashboard`) are aware of payload contract changes that affect their APIs.
- Confirm availability of Python 3.11 or `typing_extensions` features needed for `NotRequired` annotations.

## Testing & Validation Strategy
- Static: `mypy --strict src/Medical_KG/ingestion src/Medical_KG/ir` with zero new suppressions.
- Unit: `pytest -q tests/ingestion tests/ir` plus targeted adapter fixture tests.
- Integration: Run ingestion pipeline smoke tests if available; validate sample payloads end-to-end.
- Chaos/Resilience: Execute `ops/chaos/chaos_tests.sh` to ensure fault-injection flows still handle new payload types gracefully.

## Rollout & Communication
- Merge refactor behind feature flag or staged rollout if necessary; otherwise plan a coordinated deploy window.
- Announce the change via engineering updates, including migration notes for contributors.
- Monitor ingestion metrics and error dashboards post-deploy; prepare quick rollback path if downstream services fail to parse payloads.

## Acceptance Criteria
- All adapters compile against the new TypedDict aliases without casts or ignore directives.
- `Document.raw` and downstream IR components rely exclusively on the refined union.
- Documentation and examples reflect the updated payload contracts.
- Required validations pass: `mypy --strict`, `pytest -q`, and chaos tests relevant to ingestion.
- Stakeholders sign off that payload schemas are understandable and enforceable for future work.
