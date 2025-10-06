## 1. Baseline Analysis
- [ ] 1.1 Capture failing pytest cases and map to modules (config, security, ops, ingestion, IR).
- [ ] 1.2 Confirm current YAML fixtures under `tests/config`, `tests/security`, `ops/load_test` reflect expected mapping payloads.
- [ ] 1.3 Inspect `Medical_KG/config/schema.py`, `ConfigManager`, and CLI tooling for validator interface changes.

## 2. YAML parsing hardening
- [ ] 2.1 Update shared YAML loader utilities (or introduce one) returning `dict[str, Any]` for mapping documents.
- [ ] 2.2 Modify config fixture writers to emit valid YAML documents with explicit `---` boundaries when needed.
- [ ] 2.3 Update `LicenseRegistry.from_yaml` to operate on parsed dicts; add defensive type checks with actionable errors.
- [ ] 2.4 Ensure load-test budget loader returns structured mapping; adjust tests for new behaviour.

## 3. Config schema validation alignment
- [ ] 3.1 Integrate `jsonschema` validator factory consistent with optimization proposal #3.
- [ ] 3.2 Restore CLI `--schema` validation by adapting `_Validator` wrapper to expose `validate` method.
- [ ] 3.3 Update tests under `tests/config/test_cli.py` and `tests/ingestion/test_ingestion_cli.py` to assert new messaging.
- [ ] 3.4 Ensure `ConfigManager` hot-reload and policy loading use the shared YAML loader.

## 4. IR metadata and validator updates
- [ ] 4.1 Ensure `IrBuilder` normaliser emits ISO language codes (`TextNormalizer.language`).
- [ ] 4.2 Adjust `IRValidator` to accept normalised codes and provide improved error copy matching tests.
- [ ] 4.3 Update IR builder tests to assert metadata contract from legacy retirement proposal.
- [ ] 4.4 Confirm `tests/ir/test_ir_validator.py` expectation strings match validator messages.

## 5. Observability optional dependency consistency
- [ ] 5.1 Refactor `observability/logging.py` to use standardized optional dependency registry helpers.
- [ ] 5.2 Ensure mypy strict compliance (no `Any` leakage) with helper functions.
- [ ] 5.3 Document usage in `docs/logging.md` referencing install hints.

## 6. Test coverage and validation
- [ ] 6.1 Add regression tests for YAML loader behaviour (config + security + ops budgets).
- [ ] 6.2 Extend CLI e2e tests ensuring schema validation success/failure scenarios work under new validator.
- [ ] 6.3 Re-run `ruff`, `mypy --strict`, and `pytest -q`; capture outputs.
- [ ] 6.4 Update CHANGELOG and legacy retirement/optimization documentation to note implementation completion.
- [ ] 6.5 Provide rollout checklist (config reload, license checks, load test threshold verification).

## 7. Deployment & Monitoring
- [ ] 7.1 Document release steps ensuring configuration snapshots validated prior to deploy.
- [ ] 7.2 Update monitoring guidance for JSON schema validation errors and license enforcement logs.
- [ ] 7.3 Post-deploy verification plan covering ingestion CLI, config reload, and load-test evaluation.
