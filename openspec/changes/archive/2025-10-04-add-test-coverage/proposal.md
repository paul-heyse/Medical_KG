## Why
Test coverage sits at 79% (per pytest --cov). Critical subsystems have large blind spots (briefing, ingestion adapters, IR validators, command-line tooling). Failing tests reveal missing fixtures, external dependency mocks, and schema refs. Without comprehensive tests, regressions slip through and deployments require manual validation.

## What Changes
- Stabilize existing suite: fix import/export issues, mock external services, resolve schema references, ensure deterministic fixtures.
- Achieve 100% coverage across src/Medical_KG by adding unit, integration, and property tests; cover error branches, retries, and edge cases.
- Introduce coverage enforcement in CI (threshold gate, reporting, per-module budgets).
- Provide scaffolding for future tests (factories, fixtures, helpers) and documentation on testing strategy.

## Impact
- **Specs**: new `testing` capability requirements covering coverage thresholds, deterministic fixtures, external mocking, and CI enforcement.
- **Code**: extensive tests additions across briefing, ingestion, IR, KG, retrieval, security, CLI, embeddings; possible refactors for testability.
- **Tooling**: coverage reports stored as artifacts, badge & dashboard updates.
- **Risk**: large diff surface; mitigated via incremental PRs and shared test utilities.
