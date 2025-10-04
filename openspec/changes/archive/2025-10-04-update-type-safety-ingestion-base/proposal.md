## Why
The ingestion stack still relies on loosely typed adapters, HTTP responses, and ledger utilities. This leaks `Any` throughout ClinicalTrials/openFDA/DailyMed pipelines, complicates error handling, and prevents strict mypy from succeeding when the ingestion modules are included. Breaking the work out from the broader core-services initiative lets us focus on the ingestion foundation in a contained change.

## What Changes
- Define TypedDict payloads for each ingestion adapter (clinical, guideline, literature, terminology) and ensure parse/validate stages return typed `Document` instances.
- Annotate the ingestion CLI, registry, ledger, and utils so state transitions and doc IDs remain type-safe.
- Replace `Any`-based HTTP client responses with typed wrappers (JSON/text/bytes) and expose typed retry/metric hooks.
- Update existing unit tests (or add new fakes) so they use typed fixtures rather than raw dicts.
- Run strict mypy over `src/Medical_KG/ingestion` and wire the target into the CI typing job.

## Impact
- **Specs**: `type-safety`
- **Code**: `src/Medical_KG/ingestion/**`, `tests/ingestion/**`
- **Tooling**: mypy configuration widened to include ingestion modules; optional JSON schema helpers may require stub packages
- **Risks**: schema mismatches or serialization regressions; mitigated via expanded adapter tests
