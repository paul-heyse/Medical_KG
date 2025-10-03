# Implementation Tasks

## 1. Config & Optional Dependencies

- [ ] 1.1 Annotate `config/manager.py` helpers, removing `Any`-based deep merges
- [ ] 1.2 Type `utils/optional_dependencies.py` protocols and fallbacks, covering prometheus/tiktoken/torch
- [ ] 1.3 Update CLI entrypoints to propagate typed config objects

## 2. Ingestion Modules

- [ ] 2.1 Introduce TypedDict payloads for clinical/literature/guideline adapters
- [ ] 2.2 Type HTTP client responses (retry metadata, metrics hooks)
- [ ] 2.3 Ensure ledger and registry utilities expose typed states

## 3. Retrieval & Briefing APIs

- [ ] 3.1 Finalize `api/auth`, `api/models`, and `api/routes` annotations (no unchecked dicts)
- [ ] 3.2 Type retrieval service (cache entries, fusion results, error envelopes)
- [ ] 3.3 Align briefing repository/service DTOs with typed API interfaces

## 4. Knowledge Graph Writer

- [ ] 4.1 Type `kg/writer.py` payloads (nodes, relationships) and merge helpers
- [ ] 4.2 Provide TypedDicts for KG write statements used in tests

## 5. Validation & CI

- [ ] 5.1 Run `mypy --strict` on updated modules (config, ingestion, retrieval, kg)
- [ ] 5.2 Update `docs/type_safety.md` with new protocols and examples
- [ ] 5.3 Ensure pre-commit/CI jobs enforce strict typing for these paths
