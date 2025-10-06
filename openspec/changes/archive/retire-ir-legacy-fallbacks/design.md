## Context
Typed payload follow-up work established structured `AdapterDocumentPayload` TypedDicts across ingestion adapters. The IR layer, however, still carries legacy fallback code that synthesises placeholder `raw` payloads, coerces language codes, and silently accepts incomplete metadata. These behaviours contradict the retirement package’s goal of enforcing typed, provenance-rich IR documents and continue to hide integration issues.

## Goals / Non-Goals
- **Goals**
  - Require typed payloads end-to-end by making `Document.raw` mandatory and strongly typed.
  - Remove fallback coercion paths in the IR builder and validator so malformed payloads fail fast.
  - Ensure adapters populate identifiers, provenance, and metadata fields aligned with the typed contracts.
  - Tighten mypy configuration for the IR module, eliminating `Any` escapes introduced for legacy support.
- **Non-Goals**
  - Rework downstream extraction/QA consumers; they already consume typed IR and only need updated error expectations.
  - Introduce new payload families or schema changes beyond the existing TypedDict definitions.
  - Reintroduce compatibility shims for untyped adapters—migration is complete.

## Decisions
- Update `Document`/`DocumentIR` models to require `raw: AdapterDocumentPayload` and remove optional code paths.
- Strip `_synthesise_raw_payload` and similar helpers from `IrBuilder`, ensuring adapters deliver complete payloads.
- Extend `IRValidator` to enforce language normalization (ISO-639-1), identifier parity, and provenance checks per payload family.
- Adapt tests to construct typed fixtures, covering error cases for missing identifiers, invalid language codes, and provenance mismatches.
- Enable `mypy --strict` for `Medical_KG/ir` and fail the build on new `Any` usage.

## Risks / Trade-offs
- **Risk:** Any adapter still emitting partial payloads will now fail validation. *Mitigation:* Audit adapters before rollout and provide targeted fixes.
- **Risk:** Downstream tools expecting legacy error messages may require updates. *Mitigation:* Preserve key phrasing in new validation errors and coordinate documentation updates.
- **Trade-off:** Slightly higher upfront validation cost due to stricter checks, offset by reduced fallback overhead and clearer failures.

## Migration Plan
1. Make `Document.raw` mandatory and update dataclass/type definitions accordingly.
2. Remove legacy fallback functions from the IR builder; update adapters to supply fully-typed payloads.
3. Enhance `IRValidator` with strict metadata/language/provenance enforcement and adjust error messaging.
4. Rewrite IR unit/integration tests to use typed fixtures and assert new invariants.
5. Run mypy/pytest to confirm strict compliance and update documentation describing the new behaviour.

## Open Questions
- Are there external integrations (e.g., third-party adapters) that still rely on optional raw payloads? Need confirmation before release.
- Should the validator offer a feature flag for lenient language codes during the rollout? Depends on product tolerance for breaking changes.
- Do any analytics jobs parse legacy error formats that must be updated in lockstep?
