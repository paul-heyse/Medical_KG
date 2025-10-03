# Implementation Tasks

## 1. Suppression Audit
- [x] 1.1 Enumerate all `# type: ignore` comments and justify or remove
- [x] 1.2 Inspect pyproject mypy config (exclude, ignore_missing_imports)
- [x] 1.3 Document modules relying on untyped third-party packages

## 2. Core Library Typing
- [ ] 2.1 Annotate config manager, ingestion adapters, CLI, briefing, KG writer
- [x] 2.2 Create Protocols/factories for optional dependencies (httpx, locust, torch, tiktoken, spaCy)
- [ ] 2.3 Expand pydantic shim to remove remaining fallbacks and ensure Sized checks

## 3. Service & Adapter Typing
- [ ] 3.1 Embeddings GPU validator & monitor (torch Optional, subprocess)
- [ ] 3.2 Ingestion HTTP client, rate limiter, ledger results
- [ ] 3.3 Literature/clinical adapters (Document payload TypedDicts, runtime checks)
- [ ] 3.4 Retrieval API, KG schema/writer to ensure typed payloads

## 4. Test Suite Typing
- [ ] 4.1 Update fixtures/mocks to use Protocols and annotated signatures
- [ ] 4.2 Replace sys.path hacks with importlib and typed mocks
- [ ] 4.3 Ensure conftest exposes typed monkeypatch fixture helpers

## 5. Tooling & CI
- [ ] 5.1 Configure mypy strict mode for src/Medical_KG and targeted tests
- [ ] 5.2 Integrate mypy into pre-commit and CI pipeline
- [ ] 5.3 Add coverage reports (via mypy --strict --html-report) if useful

## 6. Documentation & Governance
- [ ] 6.1 Create `docs/type_safety.md` with guidelines (optional imports, protocols, TypedDicts)
- [ ] 6.2 Update CONTRIBUTING to require annotations for new modules
- [ ] 6.3 Provide quick reference examples (async adapters, optional deps, contexts)

## 7. Verification
- [ ] 7.1 mypy --strict passes with zero ignores
- [ ] 7.2 pytest passes with typed fixtures (no runtime regressions)
- [ ] 7.3 CI gate prevents reintroduction of suppressions
