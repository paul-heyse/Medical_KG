## 1. Baseline Analysis
- [x] 1.1 Capture failing pytest cases and map to modules (config, security, ops, ingestion, IR).
- [x] 1.2 Confirm current YAML fixtures under `tests/config`, `tests/security`, `ops/load_test` reflect expected mapping payloads.
- [x] 1.3 Inspect `Medical_KG/config/schema.py`, `ConfigManager`, and CLI tooling for validator interface changes.

## 2. YAML parsing hardening
- [x] 2.1 Update shared YAML loader utilities (or introduce one) returning `dict[str, Any]` for mapping documents.
- [x] 2.2 Modify config fixture writers to emit valid YAML documents with explicit `---` boundaries when needed.
- [x] 2.3 Update `LicenseRegistry.from_yaml` to operate on parsed dicts; add defensive type checks with actionable errors.
- [x] 2.4 Ensure load-test budget loader returns structured mapping; adjust tests for new behaviour.

## 3. Config schema validation alignment
- [x] 3.1 Integrate `jsonschema` validator factory consistent with optimization proposal #3.
- [x] 3.2 Restore CLI `--schema` validation by adapting `_Validator` wrapper to expose `validate` method.
- [x] 3.3 Update tests under `tests/config/test_cli.py` and `tests/ingestion/test_ingestion_cli.py` to assert new messaging.
- [x] 3.4 Ensure `ConfigManager` hot-reload and policy loading use the shared YAML loader.

## 4. IR metadata and validator updates
- [x] 4.1 Ensure `IrBuilder` normaliser emits ISO language codes (`TextNormalizer.language`).
- [x] 4.2 Adjust `IRValidator` to accept normalised codes and provide improved error copy matching tests.
- [x] 4.3 Update IR builder tests to assert metadata contract from legacy retirement proposal.
- [x] 4.4 Confirm `tests/ir/test_ir_validator.py` expectation strings match validator messages.

## 5. Observability optional dependency consistency
- [x] 5.1 Refactor `observability/logging.py` to use standardized optional dependency registry helpers.
- [x] 5.2 Ensure mypy strict compliance (no `Any` leakage) with helper functions.
- [x] 5.3 Document usage in `docs/logging.md` referencing install hints.

## 6. Test coverage and validation
- [x] 6.1 Add regression tests for YAML loader behaviour (config + security + ops budgets).
- [x] 6.2 Extend CLI e2e tests ensuring schema validation success/failure scenarios work under new validator.
- [x] 6.3 Re-run `ruff`, `mypy --strict`, and `pytest -q`; capture outputs.
- [x] 6.4 Update CHANGELOG and legacy retirement/optimization documentation to note implementation completion.
- [x] 6.5 Provide rollout checklist (config reload, license checks, load test threshold verification).

## 7. Deployment & Monitoring
- [x] 7.1 Document release steps ensuring configuration snapshots validated prior to deploy.
- [x] 7.2 Update monitoring guidance for JSON schema validation errors and license enforcement logs.
- [x] 7.3 Post-deploy verification plan covering ingestion CLI, config reload, and load-test evaluation.
