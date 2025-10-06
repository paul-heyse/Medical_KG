## Why
The repository currently exhibits integration gaps between the optimisation programme and the legacy-retirement effort. After the recent merges, multiple runtime paths still depend on ad‑hoc behaviours that earlier OpenSpec packages deliberately removed:

- **Configuration validation** now mixes `jsonschema` with fallbacks that assume `yaml.safe_load` returns raw scalars, causing the policy loader and CLI tooling to raise `AttributeError`/`ConfigError` when configuration files resolve to plain strings.
- **Licensing enforcement** deserialises YAML streams into bare file handles, bypassing the structured entitlement checks introduced in the retirement package and leaving runtime gaps in tier/feature gating.
- **Load-test budget evaluation** expects nested mappings but currently receives string content, so regression thresholds cannot be evaluated and the operational budget CLI exits early.
- **IR validator regressions** surfaced once the legacy fallbacks were retired: language codes are not normalised, typed metadata expectations are incomplete, and provenance matching does not align with the strict contracts defined in `retire-ir-legacy-fallbacks`.
- **Optional dependency ergonomics** have slipped back to ad-hoc import guards, diverging from the standardised registry and install-hint strategy that the optimisation proposal mandated, leading to inconsistent mypy enforcement and user guidance.

Without a coordinated change the production codebase cannot realise the validated designs, the full test matrix remains red, and downstream consumers are exposed to partially-retired legacy behaviours.

## Current Issues To Resolve
1. **YAML ingestion discipline** – `ConfigManager`, license registry loaders, and load-test utilities must treat YAML documents as mappings, honouring `jsonschema`-driven structures and producing deterministic error messages.
2. **Schema tooling drift** – The CLI and test fixtures need to route through the shared `jsonschema` validator with helpful remediation hints, replacing `_Validator.validate` stubs and legacy suppression flags.
3. **IR metadata/parity gaps** – Validators, builders, and pipeline tests must enforce language normalisation (`[a-z]{2}`), typed payload identifiers, and provenance checks exactly as captured in the retirement spec.
4. **Optional dependency registry** – Observability and auxiliary modules should rely on the central dependency registry, emitting consistent `MissingDependencyError` guidance and maintaining mypy visibility over optional interfaces.
5. **Quality gate alignment** – End-to-end tests (`pytest -q`), CLI exercises, and static analysis should all execute without auxiliary patching, demonstrating that optimisation and retirement contracts coexist cleanly.

## Target Design
- **Unified YAML handling**: every loader funnels through a thin adapter that guarantees mapping-or-list return types, validating against `jsonschema` definitions and surfacing pointer-based remediation hints. This mirrors the `replace-config-validator-jsonschema` architecture while ensuring license registries and load-test budgets share the same parsing guarantees.
- **Schema validation toolchain**: the CLI delegates to `ConfigSchemaValidator` and exposes strict/lenient modes with informative output, eliminating bespoke `_Validator` instances and ensuring test fixtures cover both success and failure scenarios using structured JSON Pointer messaging.
- **Typed IR enforcement**: `IRValidator` codifies the language regex, metadata key requirements, and provenance parity defined in `retire-ir-legacy-fallbacks`; builders update their metadata population to satisfy these contracts, and regression tests assert the new invariants.
- **Optional dependency registry compliance**: modules import from `Medical_KG.utils.optional_dependencies` (or successor registry) to check availability, provide actionable install hints, and retain mypy coverage by supplying `Protocol` shims when dependencies are absent.
- **Green quality gates**: the change lands with passing test suites, updated CLI snapshots, and documentation cross-references back to the optimisation and retirement proposal packages, affirming that the production implementation now reflects the approved designs.

## What Changes
- Restore disciplined YAML parsing across configuration, licensing, security, and load-test modules using a shared loader that returns mappings/lists and emits schema-aware errors.
- Reconcile JSON schema validation flows with the central `ConfigSchemaValidator`, updating CLI commands, fixtures, and documentation to expose ergonomic strict/lenient validation modes with pointer-based hints.
- Enforce IR language normalisation and metadata expectations—identifier, version, provenance parity, and payload-family alignment—across validators, builders, and associated tests.
- Synchronise optional dependency handling with the standardised registry patterns, preserving strict mypy compliance, structured install hints, and consistent runtime diagnostics.
- Harden license registry deserialisation, config manager policy loading, and load-test budget evaluation to operate on structured YAML documents, restoring deterministic quality gate execution.

## Impact
- Affected specs: config, ingestion, ir, observability, security, ops.
- Affected code: `Medical_KG/config`, `Medical_KG/security/licenses.py`, `Medical_KG/ops/load_test/check_thresholds.py`, `Medical_KG/ir/*`, `Medical_KG/utils/optional_dependencies.py`, CLI tooling in `scripts/` and `tests/config` fixtures, plus associated tests.
- Quality gates: restores passing `pytest -q`, `mypy --strict`, and ensures CLI demos behave as documented.
