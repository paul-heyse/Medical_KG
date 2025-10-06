## Context
Recent merges introduced regressions across configuration validation, licensing enforcement, load-test budget evaluation, IR metadata enforcement, and optional dependency handling. Although the Repository Optimization and Legacy Retirement OpenSpec packages describe the desired architecture, the live code diverges: YAML payloads are treated as raw strings, the JSON schema CLI wrapper lost its `validate` method, IR documents emit languages that fail the strict validator, and optional dependency logging regressed. This proposal consolidates remediation so the code matches the validated specifications.

## Goals / Non-Goals
- **Goals**
  - Reinstate structured YAML parsing for configuration, licensing, and load-test tooling using a shared loader that guarantees mappings.
  - Align JSON schema validation (CLI and programmatic) with the `jsonschema`-based architecture documented in repository optimization proposal #3.
  - Enforce IR metadata contracts—language codes, identifiers, and error copy—consistent with legacy retirement of fallback behaviours.
  - Restore optional dependency ergonomics with typed shims, install hints, and mypy compliance as described in the optional-dependencies standardisation work.
  - Return the quality suite (`pytest`, `mypy --strict`, `ruff`) to green and document the rollout steps.
- **Non-Goals**
  - Re-designing the ingestion streaming pipeline or ledger state machine (already covered by other proposals).
  - Introducing new external dependencies beyond those captured in the optional dependency registry.
  - Revisiting retired legacy APIs (e.g., `run_async_legacy`); scope is integration, not new feature work.

## Decisions
- Provide a shared YAML loader utility returning `dict[str, Any]` (with type guards) to be used by `ConfigManager`, `LicenseRegistry`, and load-test budget readers.
- Wrap `jsonschema` validators in an adapter exposing `validate()` while preserving rich error pointers; CLI commands reuse this adapter.
- Update `IrBuilder` to propagate ISO language codes from `TextNormalizer`, and adjust `IRValidator` error messages to the format expected by updated tests.
- Implement optional dependency detection via `import_module` with runtime guard raising actionable errors; expose install hints through the dependency registry.
- Expand regression tests covering YAML parsing, schema validation exit codes, IR metadata enforcement, and CLI behaviour.

## Risks / Trade-offs
- **Risk:** Moving to a shared YAML loader could surface latent issues in callers expecting raw strings. *Mitigation:* Add explicit unit tests and ensure loader only applied where mappings are required.
- **Risk:** Updated validator messages may impact downstream scripting. *Mitigation:* Retain key substrings and document changes in release notes.
- **Trade-off:** Casting formatter classes for optional logging introduces a minor runtime risk if upstream library changes. *Mitigation:* Runtime guard raises `RuntimeError` with guidance.

## Migration Plan
1. Implement YAML loader utility; refactor config manager, license registry, and ops budget code to use it.
2. Restore JSON schema validator adapter and adjust CLI tooling + config tests.
3. Update IR builder/validator implementations and tests for language/metadata expectations.
4. Refine optional dependency handling and update documentation.
5. Run full QA (ruff, mypy, pytest); update changelog and rollout docs with verification steps.

## Open Questions
- Do any external scripts rely on previous CLI error codes/messages? Confirm with stakeholders.
- Should IR validator permit legacy language tokens for backwards compatibility? Product guidance required.
- Are there additional YAML consumers expecting string payloads? Addressed via repo-wide search during implementation.
